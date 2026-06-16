"""健康检查。"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "db": db_ok}
