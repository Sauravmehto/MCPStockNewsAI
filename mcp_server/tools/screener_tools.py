"""Screener-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response
from mcp_server.services.base import validate_symbol
from mcp_server.tools.common import ensure_data

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_screener_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Screen symbols by simple stateless filters.")
    def run_screener(
        symbols: list[str],
        minPrice: float | None = None,
        maxPrice: float | None = None,
        sector: str | None = None,
    ) -> str:
        normalized = [validate_symbol(symbol) for symbol in symbols]
        result = services.screener.screen(normalized, min_price=minPrice, max_price=maxPrice, sector_hint=sector)
        rows = ensure_data(result.data, result.error)
        return format_response(
            title="Screener results",
            source=result.source,
            warning=result.warning,
            lines=rows or ["No matches for current criteria."],
        )


