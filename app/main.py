"""FastAPI 入口。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.config import settings

app = FastAPI(title="Ragent Python", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一前缀（对应原 /api/ragent）
app.include_router(health.router, prefix=settings.app_context_path)


@app.get("/")
async def root() -> dict:
    return {"service": "ragent-py", "context": settings.app_context_path}
