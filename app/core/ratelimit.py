"""P7 公平排队限流/背压:Redis ZSET 队列 + Lua 原子准入(FIFO) + 信号量(带租约)。

最多 max_concurrent 并发;其余按入队顺序等待,超时拒绝。租约 TTL 防止节点崩溃后许可泄漏。
Redis 不可用时 fail-open(放行),不阻塞主流程。
"""

from __future__ import annotations

import asyncio
import time

from app.config import settings
from app.infra.redis import get_redis

ACTIVE = "ragent:chat:active"   # ZSET: token -> 租约到期时间
QUEUE = "ragent:chat:queue"     # ZSET: token -> 入队时间(FIFO)
POLL = 0.2

# 原子准入:清过期许可 -> 若并发未满且本 token 在队首 -> 授予(写 active+移出队列)
_LUA = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[2])
local active = redis.call('ZCARD', KEYS[1])
local front = redis.call('ZRANGE', KEYS[2], 0, 0)
if active < tonumber(ARGV[3]) and front[1] == ARGV[1] then
  redis.call('ZADD', KEYS[1], tonumber(ARGV[2]) + tonumber(ARGV[4]), ARGV[1])
  redis.call('ZREM', KEYS[2], ARGV[1])
  return 1
end
return 0
"""


async def acquire(token: str) -> bool:
    """抢许可。成功 True;等待超时返回 False。Redis 异常则 fail-open True。"""
    try:
        r = get_redis()
        await r.zadd(QUEUE, {token: time.time()})
        deadline = time.time() + settings.rag_max_wait_seconds
        while True:
            now = time.time()
            granted = await r.eval(
                _LUA, 2, ACTIVE, QUEUE,
                token, str(now), str(settings.rag_max_concurrent), str(settings.rag_lease_seconds),
            )
            if int(granted) == 1:
                return True
            if now >= deadline:
                await r.zrem(QUEUE, token)
                return False
            await asyncio.sleep(POLL)
    except Exception:
        return True  # fail-open


async def release(token: str) -> None:
    try:
        r = get_redis()
        await r.zrem(ACTIVE, token)
        await r.zrem(QUEUE, token)
    except Exception:
        pass
