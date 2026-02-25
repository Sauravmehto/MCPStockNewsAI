"""Options-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response
from mcp_server.services.base import validate_symbol
from mcp_server.tools.common import ensure_data

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_options_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get options chain.")
    def get_options_chain(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.options.get_chain(symbol)
        chain = ensure_data(result.data, result.error)
        lines = [
            f"{c.call_put.upper()} strike {c.strike:.2f} exp {c.expiration} "
            f"iv={c.implied_volatility if c.implied_volatility is not None else 'n/a'} "
            f"oi={c.open_interest if c.open_interest is not None else 'n/a'}"
            for c in chain[:30]
        ]
        return format_response(
            title=f"Options chain for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )

    @mcp.tool(description="Get implied volatility summary.")
    def get_options_iv(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.options.get_iv_summary(symbol)
        payload = ensure_data(result.data, result.error, "No IV data found.")
        return format_response(
            title=f"IV summary for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v:.6f}" for k, v in payload.items()],
        )

    @mcp.tool(description="Get options Greeks summary.")
    def get_options_greeks(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.options.get_greeks_summary(symbol)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Greeks summary for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v:.6f}" for k, v in payload.items()],
        )

    @mcp.tool(description="Get unusual options activity by volume/open-interest ratio.")
    def get_unusual_options_activity(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.options.get_unusual_activity(symbol)
        rows = ensure_data(result.data, result.error)
        return format_response(
            title=f"Unusual options activity for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=rows or ["No unusual contracts identified in current sample."],
        )

    @mcp.tool(description="Estimate max pain strike.")
    def get_max_pain(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.options.get_max_pain(symbol)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Max pain estimate for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v}" for k, v in payload.items()],
        )


