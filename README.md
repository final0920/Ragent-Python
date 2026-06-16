# Ragent Python

`nageoffer/ragent`（Java/Spring Boot 企业级 RAG）的 **Python 全栈复刻**，技术栈 **FastAPI + LangGraph + pgvector + Redis + Ollama**。
当前里程碑：**MVP 最小可演示问答闭环**（上传文档 → 混合检索[向量+BM25+RRF]+重排 → LangGraph 编排 → SSE 流式问答）。

## 环境（uv）

```bash
uv sync
cp .env.example .env          # 按需改
docker compose up -d          # postgres(pgvector) + redis + ollama
# 拉模型：docker exec -it <ollama> ollama pull qwen2.5:7b && ollama pull bge-m3
uv run uvicorn app.main:app --host 0.0.0.0 --port 9090
# 健康检查：GET http://localhost:9090/api/ragent/health
```

## 结构

```
app/
  config.py        集中配置(pydantic-settings)
  db.py            异步引擎/会话(SQLAlchemy 2 + asyncpg)
  models.py        ORM(MVP 子集)
  main.py          FastAPI 入口
  api/             路由：health(已) / knowledge(摄取) / chat(SSE)
  infra/           模型客户端：embedding / chat(流式) / rerank（OpenAI 兼容 httpx）
  core/            检索：向量+BM25+RRF+去重+重排
  graph/           LangGraph 主图：load_memory→retrieve→build_prompt→stream_llm
deploy/sql/schema.sql   建表(pgvector 1536 + tsvector BM25)
docker-compose.yml
```

## 模块契约（供并行开发）

- `app/infra/clients.py`
  - `async def embed(texts: list[str]) -> list[list[float]]`
  - `async def chat_stream(messages: list[dict]) -> AsyncIterator[dict]`（yield `{type, content}`）
  - `async def rerank(query: str, docs: list[str]) -> list[float]`
- `app/core/retrieve.py`
  - `async def retrieve(session, query: str, query_vec: list[float], collection: str, topk: int) -> list[RetrievedChunk]`（向量+BM25 双路 → RRF(k=60) → 去重 → 可选重排 Top-5）
- `app/graph/pipeline.py`
  - `async def stream_chat(session, conversation_id: str, question: str) -> AsyncIterator[dict]`（LangGraph 编排，yield SSE 事件）

> 复刻设计依据见 `../Ragent-Python全栈复刻-实施计划.md`。
