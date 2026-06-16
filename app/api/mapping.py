"""词典归一化映射 CRUD(query_term_mapping)。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import QueryTermMapping
from app.utils import gen_id

router = APIRouter(tags=["mapping"])


class MappingIn(BaseModel):
    source_term: str
    target_term: str
    domain: str = ""
    match_type: int = 1
    priority: int = 100


@router.get("/mappings")
async def list_mappings(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(QueryTermMapping).where(QueryTermMapping.deleted.is_(False)).order_by(QueryTermMapping.priority)
        )
    ).scalars().all()
    return [
        {"id": r.id, "source_term": r.source_term, "target_term": r.target_term,
         "domain": r.domain, "priority": r.priority, "enabled": r.enabled}
        for r in rows
    ]


@router.post("/mappings")
async def create_mapping(body: MappingIn, session: AsyncSession = Depends(get_session)) -> dict:
    m = QueryTermMapping(id=gen_id(), **body.model_dump())
    session.add(m)
    await session.commit()
    return {"id": m.id}


@router.delete("/mappings/{mid}")
async def delete_mapping(mid: str, session: AsyncSession = Depends(get_session)) -> dict:
    m = (await session.execute(select(QueryTermMapping).where(QueryTermMapping.id == mid))).scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=404, detail="映射不存在")
    m.deleted = True
    await session.commit()
    return {"deleted": True}
