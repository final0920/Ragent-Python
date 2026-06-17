"""Celery 异步任务:文档分块入库(上传后异步处理,接口快速返回)。"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.celery_app import celery
from app.db import SessionLocal
from app.models import KnowledgeDocument
from app.services.ingest import ingest_text


@celery.task(name="chunk_ingest")
def chunk_ingest_task(doc_id: str, kb_id: str, collection: str, text: str, strategy: str = "fixed_size") -> int:
    async def _do() -> int:
        async with SessionLocal() as session:
            n = await ingest_text(session, kb_id, doc_id, collection, text, strategy)
            doc = (
                await session.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
            ).scalar_one_or_none()
            if doc:
                doc.status, doc.chunk_count = "done", n
                await session.commit()
            return n

    return asyncio.run(_do())
