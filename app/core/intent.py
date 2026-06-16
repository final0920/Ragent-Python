"""P5 意图识别与路由：意图树叶子 LLM 批量打分 → 封顶 → 分数驱动检索路由。"""

from __future__ import annotations

import json
import re

from sqlalchemy import select

from app.config import settings
from app.infra import clients
from app.models import IntentNode


async def load_leaf_nodes(session) -> list[IntentNode]:
    """加载可打分的叶子意图（level==2，启用，未删）。"""
    return list(
        (
            await session.execute(
                select(IntentNode).where(
                    IntentNode.level == 2,
                    IntentNode.enabled.is_(True),
                    IntentNode.deleted.is_(False),
                )
            )
        ).scalars().all()
    )


def _extract_json(text: str):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


async def classify(query: str, leaves: list[IntentNode]) -> list[tuple[IntentNode, float]]:
    """一次 LLM 调用给所有叶子打分，返回 [(node, score)] 降序。"""
    if not leaves:
        return []
    listing = "\n".join(
        f"- code={n.intent_code} | 名称={n.name} | 说明={n.description or ''} | 示例={n.examples or ''}"
        for n in leaves
    )
    prompt = [
        {"role": "system", "content": "你是意图分类器。给每个候选意图对用户问题的相关度打分(0~1)。只输出 JSON 数组，元素 {\"code\":..,\"score\":..}，不要多余文字。"},
        {"role": "user", "content": f"用户问题：{query}\n\n候选意图：\n{listing}"},
    ]
    try:
        raw = await clients.chat(prompt, temperature=0.1)
    except Exception:
        return []
    by_code = {n.intent_code: n for n in leaves}
    scored: list[tuple[IntentNode, float]] = []
    for item in _extract_json(raw):
        code = item.get("code") if isinstance(item, dict) else None
        node = by_code.get(code)
        if node is None:
            continue
        try:
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        scored.append((node, score))
    scored.sort(key=lambda x: -x[1])
    return scored


def resolve(scored: list[tuple[IntentNode, float]]) -> list[tuple[IntentNode, float]]:
    """阈值过滤 + 封顶。"""
    kept = [(n, s) for n, s in scored if s >= settings.rag_intent_min_score]
    return kept[: settings.rag_intent_max_count]


async def route(session, query: str) -> dict:
    """返回 {intents, collections, use_global}。无意图树则回退全局。"""
    leaves = await load_leaf_nodes(session)
    if not leaves:
        return {"intents": [], "collections": [], "use_global": True}

    resolved = resolve(await classify(query, leaves))
    collections: list[str] = []
    for node, score in resolved:
        if node.kind == 0 and node.collection_name and score >= settings.rag_intent_directed_min:
            if node.collection_name not in collections:
                collections.append(node.collection_name)
    return {
        "intents": [{"code": n.intent_code, "name": n.name, "score": s, "kind": n.kind} for n, s in resolved],
        "collections": collections,
        "use_global": not collections,
    }
