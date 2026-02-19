"""Fundamental-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response, line_money, line_number, line_percent
from mcp_server.services.base import validate_symbol
from mcp_server.tools.common import ensure_data

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_fundamental_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get key financial metrics for a ticker.")
    def get_key_financials(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.fundamental.get_metrics(symbol)
        item = ensure_data(result.data, result.error)
        return format_response(
            title=f"Key financials for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[
                line_number("P/E", item.pe_ratio),
                line_number("EPS", item.eps),
                line_number("Book Value", item.book_value),
                line_percent("Dividend Yield", item.dividend_yield),
                line_money("52W High", item.week_52_high),
                line_money("52W Low", item.week_52_low),
                line_money("Market Cap", item.market_capitalization),
                line_number("Beta", item.beta),
            ],
        )

    @mcp.tool(description="Get normalized financial statements.")
    def get_financial_statements(symbol: str, statementType: str = "income", period: str = "annual") -> str:
        symbol = validate_symbol(symbol)
        result = services.fundamental.get_statement(symbol, statement_type=statementType, period=period)
        rows = ensure_data(result.data, result.error)
        lines = [f"{row.period or 'n/a'} | type={row.statement_type}" for row in rows]
        return format_response(
            title=f"Financial statements for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )

    @mcp.tool(description="Get fundamental ratings approximation.")
    def get_fundamental_ratings(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.fundamental.get_ratings(symbol)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Fundamental rating for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v}" for k, v in payload.items()],
        )

    @mcp.tool(description="Get implied price target snapshot.")
    def get_price_targets(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.fundamental.get_targets(symbol)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Price target estimate for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v}" for k, v in payload.items()],
        )

    @mcp.tool(description="Get insider/institutional ownership signal snapshot.")
    def get_ownership_signals(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.fundamental.get_ownership_snapshot(symbol)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Ownership signals for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"{k}: {v}" for k, v in payload.items()],
        )

    @mcp.tool(description="Get SEC filing metadata.")
    def get_sec_filings(symbol: str, limit: int = 10) -> str:
        symbol = validate_symbol(symbol)
        result = services.fundamental.get_sec_filings(symbol, limit=limit)
        filings = ensure_data(result.data, result.error)
        lines = [f"{f.filed_at} | {f.form} | {f.filing_url or 'n/a'}" for f in filings]
        return format_response(
            title=f"SEC filings for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )


