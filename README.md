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

## 前端（React 18 + Vite + TS + Zustand）

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 （已代理 /api -> 后端 9090）
npm run build      # 产物 frontend/dist
```

页面：智能问答（SSE 流式 + 停止 + 引用/意图展示）、知识库（建库/列表/上传）、意图树（叶子意图增查）。

## P1 多模型路由 + 熔断

chat / chat_stream 走多模型路由：按优先级 failover、流式首包探测(60s 超时判活)、三态熔断（连续失败 2 次→OPEN 30s→HALF_OPEN 放行 1 探测）。

- 配主+备模型：`.env` 的 `LLM_FALLBACKS`（JSON 数组，缺省字段继承主模型）。
- 查看候选与熔断状态：`GET /api/ragent/rag/models`。
- 主模型挂了自动切备用；恢复后探测回 CLOSED。embed/rerank 保持单模型+重试。

## P8 MCP 工具调用

知识库答不了的问题可路由到 MCP 工具查实时数据。默认关闭，开启步骤：

```bash
uv sync --group mcp
uv run python mcp_server/server.py      # 启动工具服务 127.0.0.1:9099/mcp（sales_query/ticket_query/weather_query）
# .env 设 MCP_ENABLED=true（MCP_SERVER_URL 默认 http://127.0.0.1:9099/mcp）
# 在意图树新增 kind=MCP 的叶子，mcp_tool_id 填工具名(如 weather_query)
```

链路：意图命中 MCP 叶子 → LLM 按工具 inputSchema 抽参 → 调用工具 → 结果作为【工具实时数据】注入 Prompt。服务未起/未装时自动降级（不影响 KB 问答）。

## P9 RAGAS 评测

ragas 为可选重依赖，单独装：`uv sync --group eval`。四段流程：

```bash
uv run python -m app.evaluation init                                   # 写种子评估集 app/evaluation/eval_set.json
uv run python -m app.evaluation run   --out runs/base.json             # 录制(需在线服务+已摄取数据)
uv run python -m app.evaluation score --run runs/base.json --out runs/base_scores.json --ragas-n 3
uv run python -m app.evaluation report --scores runs/base_scores.json --out-dir runs/base_report
# 基线 vs 优化对比(改 .env 后再跑一组 opt)：
uv run python -m app.evaluation compare --a runs/base_scores.json --b runs/opt_scores.json
```

- 五指标：faithfulness / answer_relevancy / answer_correctness / context_precision / context_recall。
- judge LLM 与 embeddings 走本地 OpenAI 兼容端点（同 .env 配置）。
- **诚实量化建议**：先关掉 RRF/重排跑一组基线，再开启跑一组优化，用 `compare` 得到真实提升——这是简历里"准确率 X%→Y%"的正确测法。
- 单题快速手测：`GET /api/ragent/rag/eval?question=...`（返回答案+上下文+意图，不跑 RAGAS）。

> 复刻设计依据见 `../Ragent-Python全栈复刻-实施计划.md`。
