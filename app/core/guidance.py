"""歧义澄清:单子问且两个相近 KB 候选难分时,产出澄清问题短路,不直接检索作答。"""

from __future__ import annotations

from app.config import settings


def detect(intents: list[dict], sub_questions: list[str]) -> str | None:
    """返回澄清问题(触发)或 None(不触发)。intents 已按分数降序。"""
    if not settings.rag_guidance_enabled:
        return None
    if len(sub_questions or []) > 1:
        return None  # 多子问不澄清
    kb = [i for i in intents if i.get("kind") == 0]
    if len(kb) < 2:
        return None
    top, second = float(kb[0].get("score", 0)), float(kb[1].get("score", 0))
    if top <= 0:
        return None
    if second / top >= settings.rag_guidance_ratio and (top - second) < settings.rag_guidance_margin:
        return (
            f"你的问题可能涉及「{kb[0]['name']}」或「{kb[1]['name']}」,"
            "请补充说明具体指哪一类,以便我更准确地回答。"
        )
    return None
