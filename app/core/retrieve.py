"""混合检索：向量召回 + BM25 召回 + RRF 融合 + 可选重排。

复用契约：
- app.config.settings：RAG 参数 / rerank 开关
- app.infra.clients.embed / rerank：embedding 与重排客户端
- app.core.types.RetrievedChunk：返回结构
- knowledge_vector(id, content, embedding vector(1024), metadata jsonb, content_tsv tsvector)

向量列按余弦距离 `embedding <=> :qvec` 排序；BM25 用 jieba 分词组 to_tsquery('simple', ...)。
元数据过滤 metadata->>'collection_name'=:collection。
"""

from __future__ import annotations

import jieba
from sqlalchemy import text

from app.config import settings
from app.core.types import RetrievedChunk
from app.infra import clients


def rrf_fuse(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion。

    输入多路有序 id 列表，输出 id -> 累加 RRF 分数 sum(1/(k+rank))，rank 从 1 开始。
    纯函数，可单测。
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def _build_tsquery(query: str) -> str:
    """jieba 分词 -> simple 配置的 to_tsquery 字符串（' | ' 连接）。"""
    tokens = [t.strip() for t in jieba.lcut(query) if t.strip()]
    # 去重保序，去掉 tsquery 语法保留字符避免解析错误
    seen: set[str] = set()
    cleaned: list[str] = []
    for tok in tokens:
        safe = "".join(c for c in tok if c not in "&|!():*<>'\" \t\n")
        if safe and safe not in seen:
            seen.add(safe)
            cleaned.append(safe)
    return " | ".join(cleaned)


async def _dense_recall(
    session, qvec: list[float], collection: str, topk: int
) -> list[tuple[str, str, dict]]:
    """向量召回：返回 [(id, content, metadata), ...]，按余弦距离升序。"""
    qvec_str = "[" + ",".join(str(x) for x in qvec) + "]"
    sql = text(
        """
        SELECT id, content, metadata
        FROM knowledge_vector
        WHERE metadata->>'collection_name' = :collection
        ORDER BY embedding <=> CAST(:qvec AS vector)
        LIMIT :topk
        """
    )
    result = await session.execute(
        sql, {"collection": collection, "qvec": qvec_str, "topk": topk}
    )
    return [(row[0], row[1], row[2] or {}) for row in result.fetchall()]


async def _sparse_recall(
    session, query: str, collection: str, topk: int
) -> list[tuple[str, str, dict]]:
    """BM25 召回：jieba -> to_tsquery，ts_rank 降序。无可用词则返回空。"""
    tsq = _build_tsquery(query)
    if not tsq:
        return []
    sql = text(
        """
        SELECT id, content, metadata, ts_rank(content_tsv, query) AS rank
        FROM knowledge_vector, to_tsquery('simple', :q) AS query
        WHERE content_tsv @@ query
          AND metadata->>'collection_name' = :collection
        ORDER BY rank DESC
        LIMIT :topk
        """
    )
    result = await session.execute(
        sql, {"q": tsq, "collection": collection, "topk": topk}
    )
    return [(row[0], row[1], row[2] or {}) for row in result.fetchall()]


async def retrieve(
    session,
    query: str,
    collection: str,
    dense_topk: int = 20,
    sparse_topk: int = 20,
    rrf_k: int = 60,
    rerank_topn: int = 5,
) -> list[RetrievedChunk]:
    """混合检索主流程：向量 + BM25 -> RRF 融合 -> 可选重排 -> 截断 Top-N。"""
    # 1) 向量召回
    qvecs = await clients.embed([query])
    qvec = qvecs[0] if qvecs else []
    dense = (
        await _dense_recall(session, qvec, collection, dense_topk) if qvec else []
    )

    # 2) BM25 召回
    sparse = await _sparse_recall(session, query, collection, sparse_topk)

    # id -> (content, metadata)：保第一次出现的内容（两路内容应一致）
    meta_by_id: dict[str, tuple[str, dict]] = {}
    for cid, content, meta in dense:
        meta_by_id.setdefault(cid, (content, meta))
    for cid, content, meta in sparse:
        meta_by_id.setdefault(cid, (content, meta))

    # 3) RRF 融合（两路有序 id 列表）
    dense_ids = [cid for cid, _, _ in dense]
    sparse_ids = [cid for cid, _, _ in sparse]
    fused_scores = rrf_fuse([dense_ids, sparse_ids], k=rrf_k)
    fused_ids = sorted(fused_scores, key=lambda i: fused_scores[i], reverse=True)

    if not fused_ids:
        return []

    # 4) 重排或直接取融合结果
    if settings.rerank_enabled:
        cand_n = max(rerank_topn * 4, 20)
        cand_ids = fused_ids[:cand_n]
        contents = [meta_by_id[i][0] for i in cand_ids]
        scores = await clients.rerank(query, contents)
        if scores:
            order = sorted(
                range(len(cand_ids)), key=lambda j: scores[j], reverse=True
            )
            top_ids = [cand_ids[j] for j in order][:rerank_topn]
            return [
                RetrievedChunk(
                    id=i,
                    content=meta_by_id[i][0],
                    score=float(scores[cand_ids.index(i)]),
                    source="reranked",
                    metadata=meta_by_id[i][1],
                )
                for i in top_ids
            ]

    # 无重排（未启用或失败回退）：直接取融合 Top
    top_ids = fused_ids[:rerank_topn]
    return [
        RetrievedChunk(
            id=i,
            content=meta_by_id[i][0],
            score=fused_scores[i],
            source="fused",
            metadata=meta_by_id[i][1],
        )
        for i in top_ids
    ]
