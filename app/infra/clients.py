"""模型基础设施：embedding / chat(流式) / rerank 客户端（OpenAI 兼容，httpx 异步）。

默认本地 Ollama（无 key）。带简单重试。契约见 README。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def _headers(api_key: str) -> dict:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def _batches(items: list, size: int) -> list[list]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


async def embed(texts: list[str]) -> list[list[float]]:
    """文本 -> 向量。Ollama 不分批；其它 provider 批大小 32。"""
    if not texts:
        return []
    url = settings.embedding_base_url.rstrip("/") + "/embeddings"
    batch = 0 if settings.llm_provider == "ollama" else 32
    out: list[list[float]] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for group in _batches(texts, batch):
            payload = {"model": settings.embedding_model, "input": group}
            data = await _post_json(client, url, payload, settings.embedding_api_key)
            out.extend(item["embedding"] for item in data["data"])
    return out


async def chat_stream(
    messages: list[dict], deep_thinking: bool = False
) -> AsyncIterator[dict]:
    """流式对话。yield {'type': 'response'|'think', 'content': str}。"""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_chat_model,
        "messages": messages,
        "stream": True,
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        async with client.stream(
            "POST", url, json=payload, headers=_headers(settings.llm_api_key)
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (obj.get("choices") or [{}])[0].get("delta") or {}
                if delta.get("reasoning_content"):
                    yield {"type": "think", "content": delta["reasoning_content"]}
                if delta.get("content"):
                    yield {"type": "response", "content": delta["content"]}


async def chat(messages: list[dict], temperature: float = 0.1) -> str:
    """非流式对话，返回完整文本（用于摘要、意图打分等内部调用）。"""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_chat_model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        data = await _post_json(client, url, payload, settings.llm_api_key)
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""


async def rerank(query: str, docs: list[str]) -> list[float]:
    """返回与 docs 对齐的相关性分数；未启用或失败返回 []（调用方回退）。"""
    if not settings.rerank_enabled or not settings.rerank_base_url or not docs:
        return []
    url = settings.rerank_base_url.rstrip("/") + "/rerank"
    payload = {
        "model": settings.rerank_model,
        "query": query,
        "documents": docs,
        "top_n": len(docs),
        "return_documents": False,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            data = await _post_json(client, url, payload, settings.rerank_api_key)
    except Exception:
        return []
    scores = [0.0] * len(docs)
    for r in data.get("results", []):
        idx = r.get("index")
        if isinstance(idx, int) and 0 <= idx < len(scores):
            scores[idx] = float(r.get("relevance_score", 0.0))
    return scores


async def _post_json(
    client: httpx.AsyncClient, url: str, payload: dict, api_key: str, retries: int = 2
) -> dict:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = await client.post(url, json=payload, headers=_headers(api_key))
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"POST {url} 失败: {last}")
