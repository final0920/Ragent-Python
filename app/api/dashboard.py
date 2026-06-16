"""Dashboard 概览统计。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import (
    Conversation,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
    Message,
    MessageFeedback,
)

router = APIRouter(tags=["dashboard"])


@router.get("/admin/dashboard/overview")
async def overview(session: AsyncSession = Depends(get_session)) -> dict:
    async def cnt(model, *filters) -> int:
        q = select(func.count()).select_from(model)
        for f in filters:
            q = q.where(f)
        return (await session.execute(q)).scalar() or 0

    return {
        "conversations": await cnt(Conversation, Conversation.deleted.is_(False)),
        "messages": await cnt(Message, Message.deleted.is_(False)),
        "knowledge_bases": await cnt(KnowledgeBase, KnowledgeBase.deleted.is_(False)),
        "documents": await cnt(KnowledgeDocument, KnowledgeDocument.deleted.is_(False)),
        "chunks": await cnt(KnowledgeChunk, KnowledgeChunk.deleted.is_(False)),
        "feedback_up": await cnt(MessageFeedback, MessageFeedback.vote == 1, MessageFeedback.deleted.is_(False)),
        "feedback_down": await cnt(MessageFeedback, MessageFeedback.vote == -1, MessageFeedback.deleted.is_(False)),
    }
