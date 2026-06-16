"""知识库摄取服务：分块 -> 入库(chunk) -> 向量化 -> 入库(vector + tsv)。"""

from __future__ import annotations

import hashlib

import jieba
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chunk import chunk_text
from app.infra import clients
from app.models import KnowledgeChunk, KnowledgeVector
from app.utils import gen_id


def _content_hash(content: str) -> str:
    return hashlib.sha1(content.encode("utf-8")).hexdigest()


async def ingest_text(
    session: AsyncSession,
    kb_id: str,
    doc_id: str,
    collection: str,
    text: str,
    strategy: str = "fixed_size",
) -> int:
    """切分文本并写入 knowledge_chunk / knowledge_vector，返回写入块数。"""
    chunks = chunk_text(text, strategy=strategy)
    if not chunks:
        return 0

    vectors = await clients.embed(chunks)
    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"embedding 数量({len(vectors)})与块数({len(chunks)})不一致"
        )

    for i, content in enumerate(chunks):
        chunk_row = KnowledgeChunk(
            id=gen_id(),
            kb_id=kb_id,
            doc_id=doc_id,
            chunk_index=i,
            content=content,
            content_hash=_content_hash(content),
            char_count=len(content),
        )
        session.add(chunk_row)

        vec_id = gen_id()
        vec_row = KnowledgeVector(
            id=vec_id,
            content=content,
            embedding=vectors[i],
            meta={
                "collection_name": collection,
                "doc_id": doc_id,
                "chunk_index": i,
            },
        )
        session.add(vec_row)
        # 需先 flush 让 vector 行存在，再用原生 SQL 维护 tsvector（simple 配置 + jieba 分词）
        await session.flush()
        tok = " ".join(jieba.lcut(content))
        await session.execute(
            sql_text(
                "UPDATE knowledge_vector SET content_tsv = to_tsvector('simple', :tok) WHERE id = :id"
            ),
            {"tok": tok, "id": vec_id},
        )

    await session.commit()
    return len(chunks)
