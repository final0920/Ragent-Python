"""FastAPI 入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, conversation, health, intent, knowledge
from app.api import eval as eval_api
from app.config import settings
from app.core.schedule import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()       # schedule_enabled=true 时启动定时同步
    yield
    stop_scheduler()


app = FastAPI(title="Ragent Python", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一前缀（对应原 /api/ragent）
app.include_router(health.router, prefix=settings.app_context_path)
app.include_router(auth.router, prefix=settings.app_context_path)
app.include_router(knowledge.router, prefix=settings.app_context_path)
app.include_router(conversation.router, prefix=settings.app_context_path)
app.include_router(intent.router, prefix=settings.app_context_path)
app.include_router(eval_api.router, prefix=settings.app_context_path)
app.include_router(chat.router, prefix=settings.app_context_path)


@app.get("/")
async def root() -> dict:
    return {"service": "ragent-py", "context": settings.app_context_path}
