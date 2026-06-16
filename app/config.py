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

    # P4 记忆摘要
    rag_summary_enabled: bool = True
    rag_summary_start_turns: int = 9
    rag_summary_max_chars: int = 200

    # P5 意图
    rag_intent_min_score: float = 0.35     # 入选阈值
    rag_intent_max_count: int = 3          # 封顶
    rag_intent_directed_min: float = 0.4   # KB 叶子达到则定向检索其 collection

    # P8 MCP 工具调用（默认关闭；开启需 uv sync --group mcp 并启动 mcp_server）
    mcp_enabled: bool = False
    mcp_server_url: str = "http://127.0.0.1:9099/mcp"

    # 歧义澄清(guidance)
    rag_guidance_enabled: bool = True
    rag_guidance_ratio: float = 0.8     # 次高/最高 >= 此值
    rag_guidance_margin: float = 0.15   # 且 最高-次高 < 此值 -> 触发澄清

    # 定时同步
    schedule_enabled: bool = False
    schedule_scan_seconds: int = 60

    # P1 多模型路由 + 熔断
    # 备选模型(JSON 数组)，每项 {model, base_url?, api_key?, provider?, priority?}；缺省继承主模型。
    llm_fallbacks: str = ""
    llm_first_packet_timeout: int = 60     # 流式首包探测(秒)
    breaker_fail_threshold: int = 2        # 连续失败 N 次 -> OPEN
    breaker_open_seconds: int = 30         # OPEN 持续(秒) -> HALF_OPEN


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
