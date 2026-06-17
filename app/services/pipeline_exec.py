"""摄取流水线执行:按 node_order 依次跑 source -> chunk -> index 节点。"""

from __future__ import annotations

import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chunk import chunk_text
from app.models import (
    IngestionPipelineNode,
    IngestionTask,
    IngestionTaskNode,
    KnowledgeBase,
    KnowledgeDocument,
)
from app.services.ingest import ingest_chunks
from app.utils import gen_id


async def run_pipeline(
    session: AsyncSession, pipeline_id: str, kb_id: str, input_text: str = "", doc_name: str = "pipeline-doc"
) -> dict:
    kb = (
        await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    ).scalar_one_or_none()
    if kb is None:
        return {"status": "failed", "error": "知识库不存在"}

    nodes = (
        await session.execute(
            select(IngestionPipelineNode)
            .where(IngestionPipelineNode.pipeline_id == pipeline_id)
            .order_by(IngestionPipelineNode.node_order)
        )
    ).scalars().all()

    doc = KnowledgeDocument(id=gen_id(), kb_id=kb_id, doc_name=doc_name, source_type="pipeline", status="pending")
    session.add(doc)
    task = IngestionTask(id=gen_id(), pipeline_id=pipeline_id, kb_id=kb_id, doc_id=doc.id, status="running")
    session.add(task)
    await session.commit()

    ctx: dict = {"text": input_text, "chunks": None, "count": 0}
    try:
        for idx, node in enumerate(nodes):
            s = node.settings or {}
            _t = time.monotonic()
            out = ""
            if node.node_type == "source":
                if s.get("source_type") == "url" and s.get("location"):
                    async with httpx.AsyncClient(timeout=30) as c:
                        r = await c.get(s["location"])
                        r.raise_for_status()
                        ctx["text"] = r.text
                out = f"{len(ctx['text'])} 字"
            elif node.node_type == "chunk":
                ctx["chunks"] = chunk_text(
                    ctx["text"], strategy=s.get("strategy", "fixed_size"),
                    size=int(s.get("size", 512)), overlap=int(s.get("overlap", 128)),
                )
                out = f"{len(ctx['chunks'])} 块"
            elif node.node_type == "index":
                chunks = ctx["chunks"] or chunk_text(ctx["text"])
                ctx["count"] = await ingest_chunks(session, kb_id, doc.id, kb.collection_name, chunks)
                out = f"入库 {ctx['count']} 块"
            session.add(IngestionTaskNode(
                id=gen_id(), task_id=task.id, node_type=node.node_type, node_order=idx,
                status="done", output=out, duration_ms=int((time.monotonic() - _t) * 1000),
            ))
            await session.commit()

        n = ctx["count"]
        doc.status, doc.chunk_count = "done", n
        task.status, task.chunk_count = "done", n
        await session.commit()
        return {"task_id": task.id, "doc_id": doc.id, "chunk_count": n, "status": "done"}
    except Exception as exc:  # noqa: BLE001
        doc.status = "failed"
        task.status, task.error = "failed", str(exc)[:500]
        await session.commit()
        return {"task_id": task.id, "doc_id": doc.id, "status": "failed", "error": str(exc)[:200]}
