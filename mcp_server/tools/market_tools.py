"""Market-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response
from mcp_server.tools.common import ensure_data

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_market_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get market status.")
    def get_market_status() -> str:
        result = services.market.get_market_status()
        payload = ensure_data(result.data, result.error)
        return format_response(
            title="Market status",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v}" for k, v in payload.items()],
        )

    @mcp.tool(description="Get major US market index proxies using liquid ETFs.")
    def get_market_indices() -> str:
        result = services.market.get_indices()
        rows = ensure_data(result.data, result.error)
        lines = [f"{r['name']} ({r['symbol']}): {r['price']:.2f} ({r['change_pct']:.2f}%)" for r in rows]
        return format_response(
            title="Major US index snapshot",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )

    @mcp.tool(description="Get VIX snapshot.")
    def get_vix() -> str:
        result = services.market.get_vix()
        payload = ensure_data(result.data, result.error, "No VIX data returned.")
        return format_response(
            title="VIX snapshot",
            source=result.source,
            warning=result.warning,
            lines=[f"date: {payload.get('date')}", f"value: {payload.get('value')}"],
        )

    @mcp.tool(description="Get market movers (gainers/losers/active).")
    def get_market_movers(kind: str = "gainers") -> str:
        result = services.market.get_movers(kind=kind)
        rows = ensure_data(result.data, result.error)
        return format_response(
            title=f"Market movers: {kind}",
            source=result.source,
            warning=result.warning,
            lines=[f"{idx + 1}. {symbol}" for idx, symbol in enumerate(rows)],
        )

    @mcp.tool(description="Get sector performance snapshot.")
    def get_sector_performance() -> str:
        result = services.market.get_sector_performance()
        rows = ensure_data(result.data, result.error)
        return format_response(
            title="Sector performance",
            source=result.source,
            warning=result.warning,
            lines=[f"{r['sector']}: {r['change_pct']:.2f}%" for r in rows],
        )

    @mcp.tool(description="Get market breadth estimate.")
    def get_market_breadth() -> str:
        result = services.market.get_market_breadth()
        payload = ensure_data(result.data, result.error)
        return format_response(
            title="Market breadth",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v}" for k, v in payload.items()],
        )


