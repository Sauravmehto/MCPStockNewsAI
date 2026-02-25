"""Technical-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response, line_date, line_number
from mcp_server.services.base import validate_interval, validate_range, validate_symbol
from mcp_server.tools.common import ensure_data

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_technical_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get RSI from normalized candle stream.")
    def get_rsi(symbol: str, interval: str, from_unix: int, to_unix: int, period: int = 14) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.technical.get_rsi(symbol, interval, from_unix, to_unix, period=period)
        points = ensure_data(result.data, result.error)
        point = points[-1]
        zone = "overbought" if point.value >= 70 else "oversold" if point.value <= 30 else "neutral"
        return format_response(
            title=f"RSI for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[line_number("Latest RSI", point.value, 2), f"Signal zone: {zone}", line_date("Timestamp", point.timestamp)],
        )

    @mcp.tool(description="Get MACD from normalized candle stream.")
    def get_macd(
        symbol: str,
        interval: str,
        from_unix: int,
        to_unix: int,
        fastPeriod: int = 12,
        slowPeriod: int = 26,
        signalPeriod: int = 9,
    ) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.technical.get_macd(
            symbol,
            interval,
            from_unix,
            to_unix,
            fast_period=fastPeriod,
            slow_period=slowPeriod,
            signal_period=signalPeriod,
        )
        points = ensure_data(result.data, result.error)
        point = points[-1]
        return format_response(
            title=f"MACD for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[
                line_number("MACD", point.macd, 4),
                line_number("Signal", point.signal, 4),
                line_number("Histogram", point.histogram, 4),
                line_date("Timestamp", point.timestamp),
            ],
        )

    @mcp.tool(description="Get Simple Moving Average (SMA) from OHLC candles.")
    def get_sma(symbol: str, interval: str, from_unix: int, to_unix: int, period: int = 20) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        result = services.technical.get_sma(symbol, interval, from_unix, to_unix, period=period)
        point = ensure_data(result.data, result.error)
        return format_response(
            title=f"SMA({period}) for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[line_number("Latest SMA", point[1], 4), line_date("Timestamp", point[0])],
        )

    @mcp.tool(description="Get Exponential Moving Average (EMA) from OHLC candles.")
    def get_ema(symbol: str, interval: str, from_unix: int, to_unix: int, period: int = 20) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        result = services.technical.get_ema(symbol, interval, from_unix, to_unix, period=period)
        point = ensure_data(result.data, result.error)
        return format_response(
            title=f"EMA({period}) for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[line_number("Latest EMA", point[1], 4), line_date("Timestamp", point[0])],
        )

    @mcp.tool(description="Estimate support and resistance levels from recent candles.")
    def get_support_resistance_levels(
        symbol: str, interval: str, from_unix: int, to_unix: int, lookback: int = 120, levelsCount: int = 3
    ) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        result = services.technical.get_support_resistance(
            symbol, interval, from_unix, to_unix, lookback=lookback, levels_count=levelsCount
        )
        levels = ensure_data(result.data, result.error)
        return format_response(
            title=f"Support/Resistance for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[
                f"Supports: {', '.join(f'{x:.2f}' for x in levels[0]) or 'n/a'}",
                f"Resistances: {', '.join(f'{x:.2f}' for x in levels[1]) or 'n/a'}",
            ],
        )

    @mcp.tool(description="Detect chart patterns with heuristic logic.")
    def detect_chart_patterns(symbol: str, interval: str, from_unix: int, to_unix: int) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        result = services.technical.detect_patterns(symbol, interval, from_unix, to_unix)
        rows = ensure_data(result.data, result.error)
        return format_response(
            title=f"Chart pattern scan for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=rows,
        )


