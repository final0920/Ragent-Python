"""RAG 流式问答 SSE 端点 + 停止生成。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from app.db import SessionLocal
from app.graph.pipeline import stream_chat
from app.utils import gen_id

router = APIRouter(tags=["chat"])

# MVP：进程内取消注册表（taskId -> Event）。多节点需换 Redis pub/sub。
_CANCELS: dict[str, asyncio.Event] = {}


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


@router.get("/rag/v3/chat")
async def rag_chat(
    question: str = Query(...),
    conversationId: str | None = Query(None),
    collection: str | None = Query(None),
):
    cid = conversationId or gen_id()
    task_id = gen_id()
    cancel = asyncio.Event()
    _CANCELS[task_id] = cancel

    async def gen() -> AsyncIterator[dict]:
        yield _sse("meta", {"taskId": task_id, "conversationId": cid})
        try:
            async with SessionLocal() as session:
                async for item in stream_chat(session, cid, question, collection):
                    if cancel.is_set():
                        yield _sse("cancel", {"taskId": task_id})
                        break
                    yield _sse(item["event"], item["data"])
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": str(exc)[:200]})
        finally:
            _CANCELS.pop(task_id, None)

    return EventSourceResponse(gen())


@router.post("/rag/v3/stop")
async def rag_stop(taskId: str = Query(...)) -> dict:
    ev = _CANCELS.get(taskId)
    if ev:
        ev.set()
        return {"stopped": True}
    return {"stopped": False}
