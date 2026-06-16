"""三态熔断器：CLOSED -> OPEN -> HALF_OPEN。

CLOSED 正常；连续失败达阈值 -> OPEN(拒绝)；OPEN 持续到期 -> HALF_OPEN(放行 1 个探测)；
探测成功 -> CLOSED，失败 -> OPEN 重新计时。进程内、按模型 key 维护。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"


@dataclass
class _State:
    state: str = CLOSED
    fail_count: int = 0
    opened_at: float = 0.0
    half_open_inflight: bool = False


@dataclass
class ModelHealthStore:
    fail_threshold: int = 2
    open_seconds: float = 30.0
    _states: dict[str, _State] = field(default_factory=dict)

    def _s(self, key: str) -> _State:
        return self._states.setdefault(key, _State())

    def allow(self, key: str) -> bool:
        s = self._s(key)
        if s.state == CLOSED:
            return True
        if s.state == OPEN:
            if time.monotonic() - s.opened_at >= self.open_seconds:
                s.state = HALF_OPEN
                s.half_open_inflight = True
                return True  # 放行一个探测
            return False
        # HALF_OPEN
        if s.half_open_inflight:
            return False
        s.half_open_inflight = True
        return True

    def record_success(self, key: str) -> None:
        s = self._s(key)
        s.state = CLOSED
        s.fail_count = 0
        s.half_open_inflight = False

    def record_failure(self, key: str) -> None:
        s = self._s(key)
        if s.state == HALF_OPEN:
            s.state = OPEN
            s.opened_at = time.monotonic()
            s.half_open_inflight = False
            return
        s.fail_count += 1
        if s.fail_count >= self.fail_threshold:
            s.state = OPEN
            s.opened_at = time.monotonic()

    def snapshot(self) -> dict[str, str]:
        return {k: v.state for k, v in self._states.items()}
