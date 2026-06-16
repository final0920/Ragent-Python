"""知识库 API：建库/列库/上传文档（摄取）。router 不在 main 注册。"""

from __future__ import annotations

import io
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import KnowledgeBase, KnowledgeDocument
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
        status="pending",
    )
    session.add(doc)
    await session.commit()

    n = await ingest_text(
        session, kb_id=kb_id, doc_id=doc.id, collection=kb.collection_name, text=content
    )

    doc.status = "done"
    doc.chunk_count = n
    await session.commit()

    return {"doc_id": doc.id, "chunk_count": n}
