"""多模型路由：主模型 + 备选(配置)，按优先级排序，经熔断器过滤给出尝试顺序。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.config import settings
from app.infra.breaker import ModelHealthStore


@dataclass(frozen=True)
class Candidate:
    provider: str
    base_url: str
    api_key: str
    model: str
    priority: int = 100

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model}:{self.base_url}"


def _load_candidates() -> list[Candidate]:
    primary = Candidate(
        provider=settings.llm_provider,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_chat_model,
        priority=0,
    )
    cands = [primary]
    if settings.llm_fallbacks.strip():
        try:
            for i, item in enumerate(json.loads(settings.llm_fallbacks), start=1):
                cands.append(
                    Candidate(
                        provider=item.get("provider", settings.llm_provider),
                        base_url=item.get("base_url", settings.llm_base_url),
                        api_key=item.get("api_key", settings.llm_api_key),
                        model=item["model"],
                        priority=int(item.get("priority", i)),
                    )
                )
        except Exception:
            pass  # 配置坏了就只用主模型
    return sorted(cands, key=lambda c: c.priority)


_CANDIDATES = _load_candidates()
breaker = ModelHealthStore(
    fail_threshold=settings.breaker_fail_threshold,
    open_seconds=settings.breaker_open_seconds,
)


def ordered_allowed() -> list[Candidate]:
    """按优先级返回当前允许尝试的候选；若全部熔断，至少放行优先级最高者探测。"""
    allowed = [c for c in _CANDIDATES if breaker.allow(c.key)]
    return allowed or _CANDIDATES[:1]
