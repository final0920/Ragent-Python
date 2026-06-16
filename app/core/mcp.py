"""P8 MCP 工具调用客户端：列工具 → LLM 抽参 → 调用 → 结果回灌。

mcp SDK 惰性导入；服务不可用/未安装时优雅降级返回空，不影响主流程。
"""

from __future__ import annotations

import json
import re

from app.config import settings
from app.infra import clients


async def _with_session(fn):
    """连接 MCP 服务(streamable-http)并在会话内执行 fn(session)。"""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(settings.mcp_server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await fn(session)


async def list_tools() -> list[dict]:
    """返回 [{name, description, input_schema}]；失败返回 []。"""
    try:
        async def _do(session):
            resp = await session.list_tools()
            return [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema or {}}
                for t in resp.tools
            ]
        return await _with_session(_do)
    except Exception:
        return []


async def call_tool(name: str, arguments: dict) -> str:
    try:
        async def _do(session):
            res = await session.call_tool(name, arguments)
            parts = []
            for c in res.content:
                parts.append(getattr(c, "text", "") or "")
            return "\n".join(p for p in parts if p)
        return await _with_session(_do)
    except Exception as exc:  # noqa: BLE001
        return f"[工具调用失败] {name}: {str(exc)[:120]}"


def _extract_json_obj(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


async def extract_params(query: str, tool: dict) -> dict:
    """用 LLM 按工具 inputSchema 从问题抽参；白名单过滤 + 失败全默认。"""
    schema = tool.get("input_schema") or {}
    props = schema.get("properties") or {}
    if not props:
        return {}
    desc = ", ".join(f"{k}({v.get('type','string')}): {v.get('description','')}" for k, v in props.items())
    prompt = [
        {"role": "system", "content": "从用户问题中抽取工具所需参数。只输出 JSON 对象，键为参数名，无法确定的省略。不要多余文字。"},
        {"role": "user", "content": f"问题：{query}\n工具 {tool['name']} 参数：{desc}"},
    ]
    try:
        raw = await clients.chat(prompt, temperature=0.1)
    except Exception:
        return {}
    parsed = _extract_json_obj(raw)
    return {k: v for k, v in parsed.items() if k in props}  # 白名单


async def run_mcp(query: str, mcp_tool_ids: list[str]) -> str:
    """对命中的 MCP 工具：抽参→调用→拼装结果文本。失败返回 ''。"""
    if not settings.mcp_enabled or not mcp_tool_ids:
        return ""
    tools = await list_tools()
    if not tools:
        return ""
    by_name = {t["name"]: t for t in tools}
    blocks: list[str] = []
    for tid in mcp_tool_ids:
        tool = by_name.get(tid)
        if not tool:
            continue
        args = await extract_params(query, tool)
        result = await call_tool(tid, args)
        if result:
            blocks.append(f"【{tid}】\n{result}")
    return "\n\n".join(blocks)
