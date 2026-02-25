"""Stock-domain tools."""

from __future__ import annotations
import re
from dataclasses import asdict
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.runtime.response import error_response, success_response
from mcp_server.services.base import validate_interval, validate_range, validate_symbol, validate_symbols

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices

def _legacy_stock_error_response() -> str:
    return '{"error":"All stock data providers are currently unavailable. Please try again later."}'


def register_stocks_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get latest traded stock price for a ticker symbol.")
    def get_stock_price(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_quote(symbol)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = asdict(result.data)
        return success_response(result)

    @mcp.tool(description="Get extended quote fields including open, high, low, and previous close.")
    def get_quote(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_quote(symbol)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = asdict(result.data)
        return success_response(result)

    @mcp.tool(description="Get company profile details for a ticker.")
    def get_company_profile(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_profile(symbol)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = asdict(result.data)
        return success_response(result)

    @mcp.tool(description="Get OHLCV candles for a symbol within a unix timestamp range.")
    def get_candles(symbol: str, interval: str, from_unix: int, to_unix: int, limit: int = 20) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = [asdict(item) for item in result.data[-min(limit, len(result.data)) :]]
        return success_response(result)

    @mcp.tool(description="Get stock news headlines within a date window (YYYY-MM-DD).")
    def get_stock_news(symbol: str, from_date: str, to_date: str, limit: int = 10) -> str:
        symbol = validate_symbol(symbol)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", from_date) or not re.match(r"^\d{4}-\d{2}-\d{2}$", to_date):
            return error_response("INVALID_PARAMS", "from_date and to_date must be YYYY-MM-DD.")
        result = services.stocks.get_news(symbol, from_date, to_date, limit=limit)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = [asdict(item) for item in result.data]
        return success_response(result)

    @mcp.tool(description="Get dividend history from provider adapters.")
    def get_dividends(symbol: str, limit: int = 12) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_dividends(symbol, limit=limit)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = [asdict(item) for item in result.data]
        return success_response(result)

    @mcp.tool(description="Get split history from provider adapters.")
    def get_splits(symbol: str, limit: int = 10) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_splits(symbol, limit=limit)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = [asdict(item) for item in result.data]
        return success_response(result)

    @mcp.tool(description="Get earnings calendar snapshots.")
    def get_earnings_calendar(symbol: str, limit: int = 8) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_earnings_calendar(symbol, limit=limit)
        if not result.data:
            return _legacy_stock_error_response()
        result.data = [asdict(item) for item in result.data]
        return success_response(result)

    @mcp.tool(description="Get pre/post market snapshot for a symbol.")
    def get_premarket_data(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_premarket_data(symbol)
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Pre-market data unavailable.")
        return success_response(result)

    @mcp.tool(description="Search ticker symbols by company name or keyword.")
    def search_symbol(query: str) -> str:
        result = services.stocks.search_symbol(query)
        if not result.data:
            return error_response("SYMBOL_NOT_FOUND", "No matching symbols found.")
        return success_response(result)

    @mcp.tool(description="Get batch watchlist summary with quote and sentiment.")
    def get_watchlist_summary(symbols: list[str]) -> str:
        normalized = validate_symbols(symbols)
        result = services.stocks.get_watchlist_summary(normalized)
        if not result.data:
            return error_response("DATA_UNAVAILABLE", "Watchlist data unavailable.")
        return success_response(result)


