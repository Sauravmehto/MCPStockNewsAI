"""Stock-domain tools."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.services.base import validate_interval, validate_range, validate_symbol

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices

GENERIC_STOCK_ERROR = "All stock data providers are currently unavailable. Please try again later."


def _error_payload() -> str:
    return json.dumps({"error": GENERIC_STOCK_ERROR})


def _ok_payload(data: object, source: str | None, warning: str | None) -> str:
    payload: dict[str, object] = {"data": data}
    if source:
        payload["source"] = source
    if warning:
        payload["warning"] = warning
    return json.dumps(payload)


def register_stocks_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get latest traded stock price for a ticker symbol.")
    def get_stock_price(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_quote(symbol)
        if not result.data:
            return _error_payload()
        return _ok_payload(asdict(result.data), result.source, result.warning)

    @mcp.tool(description="Get extended quote fields including open, high, low, and previous close.")
    def get_quote(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_quote(symbol)
        if not result.data:
            return _error_payload()
        return _ok_payload(asdict(result.data), result.source, result.warning)

    @mcp.tool(description="Get company profile details for a ticker.")
    def get_company_profile(symbol: str) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_profile(symbol)
        if not result.data:
            return _error_payload()
        return _ok_payload(asdict(result.data), result.source, result.warning)

    @mcp.tool(description="Get OHLCV candles for a symbol within a unix timestamp range.")
    def get_candles(symbol: str, interval: str, from_unix: int, to_unix: int, limit: int = 20) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not result.data:
            return _error_payload()
        candles = [asdict(item) for item in result.data[-min(limit, len(result.data)) :]]
        return _ok_payload(candles, result.source, result.warning)

    @mcp.tool(description="Get stock news headlines within a date window (YYYY-MM-DD).")
    def get_stock_news(symbol: str, from_date: str, to_date: str, limit: int = 10) -> str:
        symbol = validate_symbol(symbol)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", from_date) or not re.match(r"^\d{4}-\d{2}-\d{2}$", to_date):
            raise ValueError("from_date and to_date must be YYYY-MM-DD.")
        result = services.stocks.get_news(symbol, from_date, to_date, limit=limit)
        if not result.data:
            return _error_payload()
        rows = [asdict(item) for item in result.data]
        return _ok_payload(rows, result.source, result.warning)

    @mcp.tool(description="Get dividend history from provider adapters.")
    def get_dividends(symbol: str, limit: int = 12) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_dividends(symbol, limit=limit)
        if not result.data:
            return _error_payload()
        rows = [asdict(item) for item in result.data]
        return _ok_payload(rows, result.source, result.warning)

    @mcp.tool(description="Get split history from provider adapters.")
    def get_splits(symbol: str, limit: int = 10) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_splits(symbol, limit=limit)
        if not result.data:
            return _error_payload()
        rows = [asdict(item) for item in result.data]
        return _ok_payload(rows, result.source, result.warning)

    @mcp.tool(description="Get earnings calendar snapshots.")
    def get_earnings_calendar(symbol: str, limit: int = 8) -> str:
        symbol = validate_symbol(symbol)
        result = services.stocks.get_earnings_calendar(symbol, limit=limit)
        if not result.data:
            return _error_payload()
        rows = [asdict(item) for item in result.data]
        return _ok_payload(rows, result.source, result.warning)


