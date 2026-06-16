"""示例问题:随机返回(欢迎页) + CRUD。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import SampleQuestion
from app.utils import gen_id

router = APIRouter(tags=["sample"])


class SampleIn(BaseModel):
    content: str


@router.get("/rag/sample-questions")
async def random_samples(
    limit: int = Query(4, ge=1, le=20), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = (
        await session.execute(
            select(SampleQuestion).where(SampleQuestion.enabled.is_(True))
            .order_by(func.random()).limit(limit)
        )
    ).scalars().all()
    return [{"id": s.id, "content": s.content} for s in rows]


@router.get("/sample-questions")
async def list_samples(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(SampleQuestion))).scalars().all()
    return [{"id": s.id, "content": s.content, "enabled": s.enabled} for s in rows]


@router.post("/sample-questions")
async def create_sample(body: SampleIn, session: AsyncSession = Depends(get_session)) -> dict:
    s = SampleQuestion(id=gen_id(), content=body.content)
    session.add(s)
    await session.commit()
    return {"id": s.id}


@router.delete("/sample-questions/{sid}")
async def delete_sample(sid: str, session: AsyncSession = Depends(get_session)) -> dict:
    s = (await session.execute(select(SampleQuestion).where(SampleQuestion.id == sid))).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="不存在")
    await session.delete(s)
    await session.commit()
    return {"deleted": True}
