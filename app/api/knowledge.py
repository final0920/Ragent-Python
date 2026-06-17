"""知识库 API：建库/列库/上传文档（摄取）。router 不在 main 注册。"""

from __future__ import annotations

import io
import re

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.infra import storage
from app.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.services.ingest import ingest_text
from app.utils import gen_id

router = APIRouter(tags=["knowledge"])


class CreateKBBody(BaseModel):
    name: str


def _slug(name: str) -> str:
    """从 name 生成 collection slug；非字母数字下划线转 _，为空则回退 gen_id。"""
    s = re.sub(r"[^0-9A-Za-z_]+", "_", name.strip().lower()).strip("_")
    return s or gen_id()


def _extract_text(filename: str, raw: bytes) -> str:
    lower = (filename or "").lower()
    if lower.endswith((".txt", ".md")):
        return raw.decode("utf-8", errors="replace")
    if lower.endswith(".pdf"):
        import fitz  # pymupdf

        parts: list[str] = []
        with fitz.open(stream=io.BytesIO(raw), filetype="pdf") as pdf:
            for page in pdf:
                parts.append(page.get_text())
        return "\n".join(parts)
    raise HTTPException(status_code=400, detail=f"不支持的文件类型: {filename}")


@router.post("/knowledge-base")
async def create_kb(
    body: CreateKBBody, session: AsyncSession = Depends(get_session)
) -> dict:
    kb = KnowledgeBase(
        id=gen_id(),
        name=body.name,
        collection_name=_slug(body.name),
    )
    session.add(kb)
    await session.commit()
    return {"id": kb.id, "name": kb.name, "collection_name": kb.collection_name}


@router.get("/knowledge-base")
async def list_kb(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.deleted.is_(False))
        )
    ).scalars().all()
    return [
        {"id": r.id, "name": r.name, "collection_name": r.collection_name}
        for r in rows
    ]


@router.post("/knowledge-base/{kb_id}/docs/upload")
async def upload_doc(
    kb_id: str,
    file: UploadFile,
    strategy: str = Query("fixed_size"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    kb = (
        await session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.deleted.is_(False)
            )
        )
    ).scalar_one_or_none()
    if kb is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    raw = await file.read()
    content = _extract_text(file.filename or "", raw)

    doc = KnowledgeDocument(
        id=gen_id(),
        kb_id=kb_id,
        doc_name=file.filename or "",
        source_type="file",
        file_type=file.content_type or "",
        file_size=len(raw),
        chunk_strategy=strategy,
        status="pending",
    )
    session.add(doc)
    await session.commit()

    # 可选:原始文件存对象存储
    if settings.s3_enabled:
        key = await storage.upload(f"docs/{doc.id}/{file.filename or 'file'}", raw, file.content_type or "")
        if key:
            doc.file_url = key
            await session.commit()

    # 可选:Celery 异步分块入库,接口快速返回
    if settings.celery_enabled:
        from app.tasks import chunk_ingest_task

        doc.status = "processing"
        await session.commit()
        chunk_ingest_task.delay(doc.id, kb_id, kb.collection_name, content, strategy)
        return {"doc_id": doc.id, "chunk_count": 0, "status": "processing"}

    n = await ingest_text(
        session, kb_id=kb_id, doc_id=doc.id, collection=kb.collection_name,
        text=content, strategy=strategy,
    )
    doc.status = "done"
    doc.chunk_count = n
    await session.commit()
    return {"doc_id": doc.id, "chunk_count": n, "status": "done"}


# ---------------- 文档管理 ----------------
@router.get("/knowledge-base/{kb_id}/docs")
async def list_docs(
    kb_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    base = select(KnowledgeDocument).where(
        KnowledgeDocument.kb_id == kb_id, KnowledgeDocument.deleted.is_(False)
    )
    total = len((await session.execute(base)).scalars().all())
    rows = (
        await session.execute(
            base.order_by(KnowledgeDocument.create_time.desc())
            .offset((page - 1) * size).limit(size)
        )
    ).scalars().all()
    return {
        "total": total, "page": page, "size": size,
        "items": [
            {
                "id": d.id, "doc_name": d.doc_name, "status": d.status,
                "chunk_count": d.chunk_count, "chunk_strategy": d.chunk_strategy,
                "source_type": d.source_type, "schedule_enabled": d.schedule_enabled,
            }
            for d in rows
        ],
    }


async def _get_doc(session, doc_id: str) -> KnowledgeDocument:
    doc = (
        await session.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == doc_id, KnowledgeDocument.deleted.is_(False)
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.get("/knowledge-base/docs/{doc_id}")
async def get_doc(doc_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    d = await _get_doc(session, doc_id)
    return {
        "id": d.id, "kb_id": d.kb_id, "doc_name": d.doc_name, "status": d.status,
        "chunk_count": d.chunk_count, "chunk_strategy": d.chunk_strategy,
        "source_type": d.source_type, "source_location": d.source_location,
        "schedule_enabled": d.schedule_enabled, "schedule_cron": d.schedule_cron,
    }


class ScheduleBody(BaseModel):
    schedule_enabled: bool = False
    schedule_cron: str = ""
    source_location: str = ""


@router.put("/knowledge-base/docs/{doc_id}/schedule")
async def set_schedule(doc_id: str, body: ScheduleBody, session: AsyncSession = Depends(get_session)) -> dict:
    d = await _get_doc(session, doc_id)
    d.schedule_enabled = body.schedule_enabled
    d.schedule_cron = body.schedule_cron
    if body.source_location:
        d.source_location = body.source_location
        d.source_type = "url"
    await session.commit()
    return {"id": d.id, "schedule_enabled": d.schedule_enabled}


@router.get("/knowledge-base/docs/{doc_id}/file")
async def doc_file(doc_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    d = await _get_doc(session, doc_id)
    if not d.file_url:
        raise HTTPException(status_code=404, detail="无对象存储文件(未启用 S3 或纯文本摄取)")
    return {"url": await storage.presigned(d.file_url)}


@router.delete("/knowledge-base/docs/{doc_id}")
async def delete_doc(doc_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    d = await _get_doc(session, doc_id)
    await session.execute(sql_text("DELETE FROM knowledge_chunk WHERE doc_id = :d"), {"d": doc_id})
    await session.execute(sql_text("DELETE FROM knowledge_vector WHERE metadata->>'doc_id' = :d"), {"d": doc_id})
    d.deleted = True
    await session.commit()
    return {"deleted": True}


# ---------------- 分块管理 ----------------
@router.get("/knowledge-base/docs/{doc_id}/chunks")
async def list_chunks(doc_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.doc_id == doc_id, KnowledgeChunk.deleted.is_(False)
            ).order_by(KnowledgeChunk.chunk_index)
        )
    ).scalars().all()
    return [
        {"id": c.id, "chunk_index": c.chunk_index, "content": c.content,
         "char_count": c.char_count, "enabled": c.enabled}
        for c in rows
    ]


@router.delete("/knowledge-base/chunks/{chunk_id}")
async def delete_chunk(chunk_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    c = (
        await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id))
    ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="分块不存在")
    # 同步删除对应向量(按 doc_id + chunk_index 定位)
    await session.execute(
        sql_text(
            "DELETE FROM knowledge_vector WHERE metadata->>'doc_id' = :d AND metadata->>'chunk_index' = :i"
        ),
        {"d": c.doc_id, "i": str(c.chunk_index)},
    )
    c.deleted = True
    await session.commit()
    return {"deleted": True}
