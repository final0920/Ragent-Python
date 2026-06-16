"""幂等迁移：对当前 DATABASE_URL 执行 deploy/sql/schema.sql（全部 CREATE ... IF NOT EXISTS）。

用法：uv run python -m app.migrate
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import text

from app.db import engine

SCHEMA = Path(__file__).resolve().parent.parent / "deploy" / "sql" / "schema.sql"


async def main() -> None:
    sql = SCHEMA.read_text(encoding="utf-8")
    async with engine.begin() as conn:
        for stmt in (s.strip() for s in sql.split(";")):
            if stmt:
                await conn.execute(text(stmt))
    print(f"migrated: {SCHEMA}")


if __name__ == "__main__":
    asyncio.run(main())
