"""定时同步:周期扫描 schedule_enabled 的 url 文档,Redis 租约防多节点重复,
hash 变更检测,变更则清旧分块/向量并重新摄取。
"""

from __future__ import annotations

import hashlib

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, text

from app.config import settings
from app.db import SessionLocal
from app.infra.redis import get_redis
from app.models import KnowledgeBase, KnowledgeDocument

_scheduler: AsyncIOScheduler | None = None


async def _lease(doc_id: str, ttl: int = 300) -> bool:
    try:
        return bool(await get_redis().set(f"ragent:sched:{doc_id}", "1", nx=True, ex=ttl))
    except Exception:
        return True  # 无 Redis -> 单机直接跑


async def _collection_of(session, kb_id: str) -> str | None:
    row = (await session.execute(select(KnowledgeBase.collection_name).where(KnowledgeBase.id == kb_id))).first()
    return row[0] if row else None


async def _purge(session, doc_id: str) -> None:
    await session.execute(text("DELETE FROM knowledge_chunk WHERE doc_id = :d"), {"d": doc_id})
    await session.execute(text("DELETE FROM knowledge_vector WHERE metadata->>'doc_id' = :d"), {"d": doc_id})


async def scan_once() -> int:
    from app.services.ingest import ingest_text  # 延迟导入避免循环

    synced = 0
    async with SessionLocal() as session:
        docs = (
            await session.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.schedule_enabled.is_(True),
                    KnowledgeDocument.source_type == "url",
                    KnowledgeDocument.deleted.is_(False),
                )
            )
        ).scalars().all()
        for d in docs:
            if not d.source_location or not await _lease(d.id):
                continue
            try:
                async with httpx.AsyncClient(timeout=30) as c:
                    resp = await c.get(d.source_location)
                    resp.raise_for_status()
                    body = resp.text
            except Exception:
                continue
            h = hashlib.sha1(body.encode("utf-8")).hexdigest()
            if h == d.last_hash:
                continue  # 内容未变
            collection = await _collection_of(session, d.kb_id)
            if not collection:
                continue
            await _purge(session, d.id)
            n = await ingest_text(session, d.kb_id, d.id, collection, body)
            d.last_hash = h
            d.chunk_count = n
            await session.commit()
            synced += 1
    return synced


def start_scheduler() -> None:
    global _scheduler
    if not settings.schedule_enabled or _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(scan_once, "interval", seconds=settings.schedule_scan_seconds, id="kb_sync")
    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
