"""单题快速评测：返回检索上下文 + 完整答案 + 命中意图（不跑 RAGAS，便于手测）。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db import SessionLocal
from app.evaluation.runner import run_once

router = APIRouter(tags=["eval"])


@router.get("/rag/eval")
async def rag_eval(question: str = Query(...), collection: str = Query("")) -> dict:
    async with SessionLocal() as session:
        answer, contexts, intents = await run_once(session, question, collection)
    return {"question": question, "answer": answer, "contexts": contexts, "intents": intents}
