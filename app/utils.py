"""通用工具：ID 生成。"""

from __future__ import annotations

import uuid


def gen_id() -> str:
    """字符串主键（替代雪花，MVP 用 uuid4 hex）。"""
    return uuid.uuid4().hex
