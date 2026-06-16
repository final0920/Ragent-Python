"""P4 补全:query 改写 + 子问题拆分(一次 LLM 调用,结合历史做指代消解)。"""

from __future__ import annotations

import json
import re

from app.core import terms as terms_mod
from app.infra import clients


def _extract_json_obj(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


async def rewrite_and_split(query: str, history: list[dict] | None = None, session=None) -> dict:
    """返回 {'rewrite': str, 'sub_questions': [str]}。失败回退原问题。

    若给定 session,先按词典归一化 query(同义词->标准词)再做 LLM 改写。
    """
    if session is not None:
        try:
            query = await terms_mod.normalize(session, query)
        except Exception:
            pass
    hist = "\n".join(f"{m['role']}: {m['content']}" for m in (history or [])[-6:])
    prompt = [
        {
            "role": "system",
            "content": (
                "你是检索查询改写器。结合对话历史把用户当前问题改写成自包含、适合检索的查询(消解指代)，"
                "并在问题包含多个独立子问题时拆分。只输出 JSON："
                '{"rewrite":"改写后的问题","sub_questions":["子问题1","子问题2"]}。'
                "单一问题时 sub_questions 只含改写后的问题。不要输出多余文字。"
            ),
        },
        {"role": "user", "content": f"对话历史:\n{hist or '(无)'}\n\n当前问题:{query}"},
    ]
    try:
        raw = await clients.chat(prompt, temperature=0.1)
    except Exception:
        return {"rewrite": query, "sub_questions": [query]}
    obj = _extract_json_obj(raw)
    rewrite = (obj.get("rewrite") or query).strip() or query
    subs = [s.strip() for s in (obj.get("sub_questions") or []) if isinstance(s, str) and s.strip()]
    return {"rewrite": rewrite, "sub_questions": subs or [rewrite]}
