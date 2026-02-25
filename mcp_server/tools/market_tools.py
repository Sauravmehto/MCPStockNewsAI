"""Market-domain tools."""

from __future__ import annotations
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.runtime.response import error_response, success_response

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_market_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get market status.")
    def get_market_status() -> str:
        result = services.market.get_market_status()
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Market status unavailable.")
        return success_response(result)

    @mcp.tool(description="Get major US market index proxies using liquid ETFs.")
    def get_market_indices() -> str:
        result = services.market.get_indices()
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Market indices unavailable.")
        return success_response(result)

    @mcp.tool(description="Get VIX snapshot.")
    def get_vix() -> str:
        result = services.market.get_vix()
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "VIX data unavailable.")
        return success_response(result)

    @mcp.tool(description="Get market movers (gainers/losers/active).")
    def get_market_movers(kind: str = "gainers") -> str:
        result = services.market.get_movers(kind=kind)
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Market movers unavailable.")
        return success_response(result)

    @mcp.tool(description="Get sector performance snapshot.")
    def get_sector_performance() -> str:
        result = services.market.get_sector_performance()
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Sector performance unavailable.")
        return success_response(result)

    @mcp.tool(description="Get market breadth estimate.")
    def get_market_breadth() -> str:
        result = services.market.get_market_breadth()
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Market breadth unavailable.")
        return success_response(result)

    @mcp.tool(description="Get market hours, next open/close, and holiday schedule.")
    def get_market_hours() -> str:
        result = services.market.get_market_hours()
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Market hours unavailable.")
        return success_response(result)

    @mcp.tool(description="Get upcoming US economic calendar events.")
    def get_economic_calendar(days_ahead: int = 7) -> str:
        result = services.market.get_economic_calendar(days_ahead=days_ahead)
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Economic calendar unavailable.")
        return success_response(result)


