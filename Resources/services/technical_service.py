"""Technical-analysis service."""

from __future__ import annotations

from mcp_server.lib.indicators import (
    calc_ema,
    calc_sma,
    calculate_macd_from_candles,
    calculate_rsi_from_candles,
    detect_chart_patterns_from_candles,
    find_support_resistance_levels,
    latest_series_value,
)
from mcp_server.providers.models import NormalizedMacdPoint, NormalizedRsiPoint
from mcp_server.services.base import ErrorEnvelope, ServiceResult
from mcp_server.services.stock_service import StockService


class TechnicalService:
    def __init__(self, stocks: StockService) -> None:
        self.stocks = stocks

    def get_rsi(
        self, symbol: str, interval: str, from_unix: int, to_unix: int, period: int = 14
    ) -> ServiceResult[list[NormalizedRsiPoint]]:
        history = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not history.data:
            return ServiceResult(data=None, source=history.source, warning=history.warning, error=history.error)
        points = calculate_rsi_from_candles(history.data, period)
        if not points:
            return ServiceResult(
                data=None,
                source=history.source,
                warning=history.warning,
                error=ErrorEnvelope(code="NOT_FOUND", message="Not enough candles to compute RSI.", retriable=False),
            )
        return ServiceResult(data=points, source=f"{history.source} + local RSI", warning=history.warning)

    def get_macd(
        self,
        symbol: str,
        interval: str,
        from_unix: int,
        to_unix: int,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> ServiceResult[list[NormalizedMacdPoint]]:
        history = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not history.data:
            return ServiceResult(data=None, source=history.source, warning=history.warning, error=history.error)
        points = calculate_macd_from_candles(history.data, fast_period, slow_period, signal_period)
        if not points:
            return ServiceResult(
                data=None,
                source=history.source,
                warning=history.warning,
                error=ErrorEnvelope(code="NOT_FOUND", message="Not enough candles to compute MACD.", retriable=False),
            )
        return ServiceResult(data=points, source=f"{history.source} + local MACD", warning=history.warning)

    def get_sma(self, symbol: str, interval: str, from_unix: int, to_unix: int, period: int = 20) -> ServiceResult[tuple[int, float]]:
        history = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not history.data:
            return ServiceResult(data=None, source=history.source, warning=history.warning, error=history.error)
        point = latest_series_value(history.data, calc_sma([c.close for c in history.data], period))
        if not point:
            return ServiceResult(
                data=None,
                source=history.source,
                warning=history.warning,
                error=ErrorEnvelope(code="NOT_FOUND", message=f"Not enough candles for SMA({period}).", retriable=False),
            )
        return ServiceResult(data=point, source=history.source, warning=history.warning)

    def get_ema(self, symbol: str, interval: str, from_unix: int, to_unix: int, period: int = 20) -> ServiceResult[tuple[int, float]]:
        history = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not history.data:
            return ServiceResult(data=None, source=history.source, warning=history.warning, error=history.error)
        point = latest_series_value(history.data, calc_ema([c.close for c in history.data], period))
        if not point:
            return ServiceResult(
                data=None,
                source=history.source,
                warning=history.warning,
                error=ErrorEnvelope(code="NOT_FOUND", message=f"Not enough candles for EMA({period}).", retriable=False),
            )
        return ServiceResult(data=point, source=history.source, warning=history.warning)

    def get_support_resistance(
        self, symbol: str, interval: str, from_unix: int, to_unix: int, lookback: int = 120, levels_count: int = 3
    ) -> ServiceResult[tuple[list[float], list[float]]]:
        history = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not history.data:
            return ServiceResult(data=None, source=history.source, warning=history.warning, error=history.error)
        levels = find_support_resistance_levels(history.data, lookback, levels_count)
        return ServiceResult(data=levels, source=history.source, warning=history.warning)

    def detect_patterns(self, symbol: str, interval: str, from_unix: int, to_unix: int) -> ServiceResult[list[str]]:
        history = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not history.data:
            return ServiceResult(data=None, source=history.source, warning=history.warning, error=history.error)
        return ServiceResult(
            data=detect_chart_patterns_from_candles(history.data),
            source=history.source,
            warning="Heuristic pattern detection.",
        )


