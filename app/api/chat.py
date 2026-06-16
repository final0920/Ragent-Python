"""RAG 流式问答 SSE 端点 + 停止生成。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from app.core.cancel import registry as cancel_registry
from app.core.ratelimit import acquire, release
from app.db import SessionLocal
from app.graph.pipeline import stream_chat
from app.utils import gen_id

router = APIRouter(tags=["chat"])


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
    cancel = await cancel_registry.register(task_id)

    async def gen() -> AsyncIterator[dict]:
        yield _sse("meta", {"taskId": task_id, "conversationId": cid})
        # 排队准入:并发满且等待超时 -> 拒绝
        if not await acquire(task_id):
            yield _sse("reject", {"reason": "系统繁忙,请稍后再试"})
            yield _sse("done", {})
            cancel_registry.unregister(task_id)
            return
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
            await release(task_id)
            cancel_registry.unregister(task_id)

    return EventSourceResponse(gen())


@router.post("/rag/v3/stop")
async def rag_stop(taskId: str = Query(...)) -> dict:
    ok = await cancel_registry.request_cancel(taskId)
    return {"stopped": ok}


@router.get("/rag/models")
async def rag_models() -> dict:
    """候选模型(按优先级) + 熔断状态。"""
    from app.infra import router as model_router

    return {
        "candidates": [
            {"model": c.model, "provider": c.provider, "priority": c.priority, "base_url": c.base_url}
            for c in model_router._CANDIDATES
        ],
        "breaker": model_router.breaker.snapshot(),
    }
