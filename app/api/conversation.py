"""会话管理:列表 / 消息 / 删除。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Conversation, Message

router = APIRouter(tags=["conversation"])


@router.get("/conversations")
async def list_conversations(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(Conversation)
            .where(Conversation.deleted.is_(False))
            .order_by(Conversation.update_time.desc())
        )
    ).scalars().all()
    return [{"conversation_id": c.conversation_id, "title": c.title} for c in rows]


@router.get("/conversations/{cid}/messages")
async def list_messages(cid: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id == cid, Message.deleted.is_(False))
            .order_by(Message.create_time.asc(), Message.id.asc())
        )
    ).scalars().all()
    return [
        {"id": m.id, "role": m.role, "content": m.content, "thinking_content": m.thinking_content}
        for m in rows
    ]


@router.delete("/conversations/{cid}")
async def delete_conversation(cid: str, session: AsyncSession = Depends(get_session)) -> dict:
    rows = (
        await session.execute(select(Conversation).where(Conversation.conversation_id == cid))
    ).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="会话不存在")
    for c in rows:
        c.deleted = True
    await session.commit()
    return {"deleted": True}
