"""News-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response
from mcp_server.services.base import validate_symbol
from mcp_server.tools.common import ensure_data, format_news_line

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_news_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get company news headlines.")
    def get_company_news(symbol: str, limit: int = 10) -> str:
        symbol = validate_symbol(symbol)
        result = services.news.get_company_news(symbol, limit=limit)
        items = ensure_data(result.data, result.error)
        lines = [format_news_line(idx + 1, item.headline, item.source, item.datetime, item.url) for idx, item in enumerate(items)]
        return format_response(
            title=f"News for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )

    @mcp.tool(description="Get broad market headlines.")
    def get_market_news(limit: int = 10) -> str:
        result = services.news.get_market_headlines(limit=limit)
        rows = ensure_data(result.data, result.error)
        return format_response(
            title="Market headlines",
            source=result.source,
            warning=result.warning,
            lines=rows,
        )


