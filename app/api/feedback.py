"""消息反馈:点赞/点踩 + 理由(每条消息一条,重复则更新)。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import MessageFeedback
from app.utils import gen_id

router = APIRouter(tags=["feedback"])


class FeedbackIn(BaseModel):
    vote: int = 0          # 1 赞 / -1 踩
    reason: str = ""
    comment: str = ""
    conversation_id: str = ""


@router.post("/conversations/messages/{message_id}/feedback")
async def submit_feedback(
    message_id: str, body: FeedbackIn, session: AsyncSession = Depends(get_session)
) -> dict:
    fb = (
        await session.execute(
            select(MessageFeedback).where(
                MessageFeedback.message_id == message_id, MessageFeedback.deleted.is_(False)
            )
        )
    ).scalars().first()
    if fb:
        fb.vote, fb.reason, fb.comment = body.vote, body.reason, body.comment
    else:
        fb = MessageFeedback(
            id=gen_id(), message_id=message_id, conversation_id=body.conversation_id,
            vote=body.vote, reason=body.reason, comment=body.comment,
        )
        session.add(fb)
    await session.commit()
    return {"id": fb.id, "vote": fb.vote}
