"""意图树管理（最小 CRUD）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import IntentNode
from app.utils import gen_id

router = APIRouter(tags=["intent"])


class IntentNodeIn(BaseModel):
    intent_code: str
    name: str
    description: str = ""
    examples: str = ""
    level: int = 2
    parent_code: str = ""
    kind: int = 0  # 0 KB / 1 SYSTEM / 2 MCP
    collection_name: str = ""
    mcp_tool_id: str = ""
    topk: int = 10


@router.post("/intent-tree")
async def create_intent(body: IntentNodeIn, session: AsyncSession = Depends(get_session)) -> dict:
    node = IntentNode(id=gen_id(), **body.model_dump())
    session.add(node)
    await session.commit()
    return {"id": node.id, "intent_code": node.intent_code}


@router.get("/intent-tree")
async def list_intents(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(IntentNode).where(IntentNode.deleted.is_(False)).order_by(IntentNode.level, IntentNode.create_time)
        )
    ).scalars().all()
    return [
        {
            "id": n.id, "intent_code": n.intent_code, "name": n.name, "level": n.level,
            "kind": n.kind, "collection_name": n.collection_name, "enabled": n.enabled,
        }
        for n in rows
    ]
