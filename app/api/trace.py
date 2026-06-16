"""RAG 全链路 Trace 查询:运行列表 + 单次各阶段耗时。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import RagTraceNode, RagTraceRun

router = APIRouter(tags=["trace"])


@router.get("/rag/traces/runs")
async def list_runs(
    limit: int = Query(50, ge=1, le=200), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = (
        await session.execute(
            select(RagTraceRun).order_by(RagTraceRun.create_time.desc()).limit(limit)
        )
    ).scalars().all()
    return [
        {"trace_id": r.trace_id, "question": r.question, "total_ms": r.total_ms, "status": r.status}
        for r in rows
    ]


@router.get("/rag/traces/runs/{trace_id}")
async def get_run(trace_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    run = (
        await session.execute(select(RagTraceRun).where(RagTraceRun.trace_id == trace_id))
    ).scalars().first()
    if run is None:
        raise HTTPException(status_code=404, detail="trace 不存在")
    nodes = (
        await session.execute(
            select(RagTraceNode).where(RagTraceNode.trace_id == trace_id).order_by(RagTraceNode.node_order)
        )
    ).scalars().all()
    return {
        "trace_id": run.trace_id, "question": run.question, "total_ms": run.total_ms,
        "nodes": [{"node_type": n.node_type, "duration_ms": n.duration_ms} for n in nodes],
    }
