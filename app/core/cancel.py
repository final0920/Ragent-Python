"""P7 取消传播(跨节点):/stop 在任一节点 -> Redis pub/sub 广播 -> 运行该流的节点中断。

本地 asyncio.Event 唤醒读循环;Redis bucket 兜底"早到取消"(订阅前已 stop);
Redis 不可用时降级为同节点取消(本地直接 set)。
"""

from __future__ import annotations

import asyncio

from app.infra.redis import get_redis

CHANNEL = "ragent:stream:cancel"


def _key(task_id: str) -> str:
    return f"ragent:stream:cancel:{task_id}"


class CancelRegistry:
    def __init__(self) -> None:
        self._events: dict[str, asyncio.Event] = {}
        self._listener: asyncio.Task | None = None

    async def _ensure_listener(self) -> None:
        if self._listener and not self._listener.done():
            return
        try:
            pubsub = get_redis().pubsub()
            await pubsub.subscribe(CHANNEL)
        except Exception:
            return  # 无 Redis -> 仅同节点取消

        async def _loop() -> None:
            try:
                async for msg in pubsub.listen():
                    if msg.get("type") != "message":
                        continue
                    ev = self._events.get(msg.get("data"))
                    if ev:
                        ev.set()
            except Exception:
                pass

        self._listener = asyncio.create_task(_loop())

    async def register(self, task_id: str) -> asyncio.Event:
        ev = asyncio.Event()
        self._events[task_id] = ev
        await self._ensure_listener()
        try:  # 早到取消:已被标记则立即生效
            if await get_redis().get(_key(task_id)):
                ev.set()
        except Exception:
            pass
        return ev

    def unregister(self, task_id: str) -> None:
        self._events.pop(task_id, None)

    async def request_cancel(self, task_id: str) -> bool:
        ev = self._events.get(task_id)
        if ev:
            ev.set()  # 同节点直接生效
        try:  # 跨节点:写标记 + 广播
            r = get_redis()
            await r.set(_key(task_id), "1", ex=1800)
            await r.publish(CHANNEL, task_id)
            return True
        except Exception:
            return ev is not None


registry = CancelRegistry()
