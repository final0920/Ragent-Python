"""独立 MCP 工具服务（FastMCP, Streamable HTTP）。

启动：uv sync --group mcp && uv run python mcp_server/server.py
默认监听 127.0.0.1:9099，端点 /mcp（与 app.config.mcp_server_url 对应）。
工具为 mock 数据，演示"知识库答不了的问题交给工具查实时数据"。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ragent-tools", host="127.0.0.1", port=9099)


@mcp.tool()
def sales_query(month: str = "本月") -> str:
    """查询指定月份的销售额。参数 month 如 '2026-06' 或 '本月'。"""
    data = {"2026-05": "￥128 万", "2026-06": "￥156 万", "本月": "￥156 万"}
    return f"{month} 销售额：{data.get(month, '￥100 万(示例)')}"


@mcp.tool()
def ticket_query(order_no: str) -> str:
    """按订单号查询工单/物流状态。参数 order_no 为订单编号。"""
    return f"订单 {order_no} 状态：已发货，预计 2 天内送达（示例数据）。"


@mcp.tool()
def weather_query(city: str = "杭州") -> str:
    """查询城市天气。参数 city 为城市名。"""
    return f"{city} 今日天气：多云，22~28℃，东南风 3 级（示例数据）。"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
