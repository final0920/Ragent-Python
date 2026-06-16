"""run 阶段：对评估集逐题跑 RAG（复用主图取上下文 + 非流式取完整答案），录制结果。

需要在线服务（DB 已建库且已摄取数据 + Ollama）。
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.db import SessionLocal
from app.evaluation.dataset import DEFAULT_PATH, load_eval_set
from app.graph.pipeline import _GRAPH
from app.infra import clients


async def run_once(session, query: str, collection: str) -> tuple[str, list[str], list[dict]]:
    cid = "eval-" + uuid.uuid4().hex  # 一次性会话，无历史
    state = await _GRAPH.ainvoke(
        {"session": session, "conversation_id": cid, "question": query, "collection": collection or None}
    )
    contexts = [c.content for c in (state.get("chunks") or [])]
    answer = await clients.chat(state["messages"], temperature=0.3)
    return answer, contexts, state.get("intents") or []


async def record(out_path: str, eval_path: Path = DEFAULT_PATH) -> int:
    samples = load_eval_set(eval_path)
    results = []
    async with SessionLocal() as session:
        for s in samples:
            try:
                answer, contexts, intents = await run_once(session, s.query, s.collection)
            except Exception as exc:  # noqa: BLE001
                answer, contexts, intents = f"[ERROR] {exc}", [], []
            results.append(
                {
                    "id": s.id, "query": s.query, "ground_truth": s.ground_truth,
                    "answer": answer, "contexts": contexts,
                    "requires_rag": s.requires_rag, "intent_l2": s.intent_l2, "intents": intents,
                }
            )
            print(f"  [run] {s.id} answer={len(answer)}字 contexts={len(contexts)}")
    Path(out_path).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"录制 {len(results)} 条 -> {out_path}")
    return len(results)
