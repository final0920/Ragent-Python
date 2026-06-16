"""集中配置（对应原 application.yaml），pydantic-settings 从环境/.env 读取。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_port: int = 9090
    app_context_path: str = "/api/ragent"

    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/ragent"
    redis_url: str = "redis://:123456@127.0.0.1:6379/0"

    # 模型（OpenAI 兼容）
    llm_provider: str = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = ""
    llm_chat_model: str = "qwen2.5:7b"
    embedding_base_url: str = "http://127.0.0.1:11434/v1"
    embedding_api_key: str = ""
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024  # bge-m3=1024；换 1536 维模型(如 qwen-emb)需同步改 schema
    rerank_enabled: bool = False
    rerank_base_url: str = ""
    rerank_api_key: str = ""
    rerank_model: str = ""

    jwt_secret: str = "change-me-in-prod"
    jwt_expire_days: int = 30

    # RAG 参数
    rag_dense_topk: int = 20
    rag_sparse_topk: int = 20
    rag_rrf_k: int = 60
    rag_rerank_topn: int = 5
    rag_history_keep_turns: int = 8
    rag_max_concurrent: int = 10
    rag_max_wait_seconds: int = 15
    rag_lease_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
