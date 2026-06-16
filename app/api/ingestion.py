"""摄取流水线:创建/列表/详情/运行。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import IngestionPipeline, IngestionPipelineNode
from app.services.pipeline_exec import run_pipeline
from app.utils import gen_id

router = APIRouter(tags=["ingestion"])


class NodeIn(BaseModel):
    node_type: str           # source | chunk | index
    settings: dict = {}


class PipelineIn(BaseModel):
    name: str
    nodes: list[NodeIn] = []


class RunIn(BaseModel):
    kb_id: str
    text: str = ""
    doc_name: str = "pipeline-doc"


@router.post("/ingestion/pipelines")
async def create_pipeline(body: PipelineIn, session: AsyncSession = Depends(get_session)) -> dict:
    pipe = IngestionPipeline(id=gen_id(), name=body.name)
    session.add(pipe)
    for i, node in enumerate(body.nodes):
        session.add(IngestionPipelineNode(
            id=gen_id(), pipeline_id=pipe.id, node_type=node.node_type, node_order=i, settings=node.settings,
        ))
    await session.commit()
    return {"id": pipe.id, "name": pipe.name, "nodes": len(body.nodes)}


@router.get("/ingestion/pipelines")
async def list_pipelines(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(IngestionPipeline).where(IngestionPipeline.deleted.is_(False))
        )
    ).scalars().all()
    return [{"id": p.id, "name": p.name} for p in rows]


@router.get("/ingestion/pipelines/{pid}")
async def get_pipeline(pid: str, session: AsyncSession = Depends(get_session)) -> dict:
    pipe = (
        await session.execute(select(IngestionPipeline).where(IngestionPipeline.id == pid))
    ).scalar_one_or_none()
    if pipe is None:
        raise HTTPException(status_code=404, detail="流水线不存在")
    nodes = (
        await session.execute(
            select(IngestionPipelineNode)
            .where(IngestionPipelineNode.pipeline_id == pid)
            .order_by(IngestionPipelineNode.node_order)
        )
    ).scalars().all()
    return {
        "id": pipe.id, "name": pipe.name,
        "nodes": [{"node_type": n.node_type, "settings": n.settings, "order": n.node_order} for n in nodes],
    }


@router.post("/ingestion/pipelines/{pid}/run")
async def run(pid: str, body: RunIn, session: AsyncSession = Depends(get_session)) -> dict:
    return await run_pipeline(session, pid, body.kb_id, input_text=body.text, doc_name=body.doc_name)
