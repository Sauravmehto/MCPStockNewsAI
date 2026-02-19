"""Risk analytics service."""

from __future__ import annotations

import math
from statistics import mean, pstdev

from mcp_server.lib.indicators import calc_returns_from_candles
from mcp_server.services.base import ErrorEnvelope, ServiceResult
from mcp_server.services.stock_service import StockService


def _std(values: list[float]) -> float:
    return pstdev(values) if len(values) > 1 else 0.0


def _max_drawdown(prices: list[float]) -> float:
    if not prices:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (p - peak) / peak if peak else 0.0
        max_dd = min(max_dd, dd)
    return max_dd


def _correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx = mean(xs)
    my = mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


class RiskService:
    def __init__(self, stocks: StockService) -> None:
        self.stocks = stocks

    def _returns(self, symbol: str, interval: str, from_unix: int, to_unix: int) -> ServiceResult[list[float]]:
        candles = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not candles.data:
            return ServiceResult(data=None, source=candles.source, warning=candles.warning, error=candles.error)
        returns = calc_returns_from_candles(candles.data)
        if not returns:
            return ServiceResult(
                data=None,
                source=candles.source,
                warning=candles.warning,
                error=ErrorEnvelope(code="NOT_FOUND", message="Not enough candles for returns.", retriable=False),
            )
        return ServiceResult(data=returns, source=candles.source, warning=candles.warning)

    def get_beta(self, symbol: str, benchmark_symbol: str, interval: str, from_unix: int, to_unix: int):
        r1 = self._returns(symbol, interval, from_unix, to_unix)
        r2 = self._returns(benchmark_symbol, interval, from_unix, to_unix)
        if not r1.data or not r2.data:
            return ServiceResult(data=None, error=r1.error or r2.error, source=r1.source or r2.source)
        n = min(len(r1.data), len(r2.data))
        xs = r1.data[-n:]
        ys = r2.data[-n:]
        my = mean(ys)
        var_y = mean([(y - my) ** 2 for y in ys]) if ys else 0.0
        cov = mean([(x - mean(xs)) * (y - my) for x, y in zip(xs, ys)]) if xs else 0.0
        beta = cov / var_y if var_y > 0 else 0.0
        return ServiceResult(data={"beta": beta}, source=r1.source or r2.source)

    def get_sharpe_sortino(self, symbol: str, interval: str, from_unix: int, to_unix: int, risk_free_rate: float = 0.0):
        r = self._returns(symbol, interval, from_unix, to_unix)
        if not r.data:
            return ServiceResult(data=None, error=r.error, source=r.source)
        avg = mean(r.data)
        stdev = _std(r.data)
        downside = _std([x for x in r.data if x < 0])
        sharpe = ((avg - risk_free_rate) / stdev) if stdev > 0 else 0.0
        sortino = ((avg - risk_free_rate) / downside) if downside > 0 else 0.0
        return ServiceResult(data={"sharpe": sharpe, "sortino": sortino}, source=r.source)

    def get_max_drawdown(self, symbol: str, interval: str, from_unix: int, to_unix: int):
        candles = self.stocks.get_history(symbol, interval, from_unix, to_unix)
        if not candles.data:
            return ServiceResult(data=None, error=candles.error, source=candles.source)
        dd = _max_drawdown([c.close for c in candles.data])
        return ServiceResult(data={"max_drawdown": dd}, source=candles.source)

    def get_var(self, symbol: str, interval: str, from_unix: int, to_unix: int, confidence: float = 0.95):
        r = self._returns(symbol, interval, from_unix, to_unix)
        if not r.data:
            return ServiceResult(data=None, error=r.error, source=r.source)
        sorted_returns = sorted(r.data)
        idx = max(0, min(len(sorted_returns) - 1, int((1 - confidence) * len(sorted_returns))))
        var = abs(sorted_returns[idx])
        return ServiceResult(data={"value_at_risk": var, "confidence": confidence}, source=r.source)

    def get_correlation(self, symbol: str, peer_symbol: str, interval: str, from_unix: int, to_unix: int):
        r1 = self._returns(symbol, interval, from_unix, to_unix)
        r2 = self._returns(peer_symbol, interval, from_unix, to_unix)
        if not r1.data or not r2.data:
            return ServiceResult(data=None, error=r1.error or r2.error, source=r1.source or r2.source)
        n = min(len(r1.data), len(r2.data))
        corr = _correlation(r1.data[-n:], r2.data[-n:])
        return ServiceResult(data={"correlation": corr}, source=r1.source or r2.source)

    def get_rebalance_plan(self, current_weights: dict[str, float], target_weights: dict[str, float]) -> ServiceResult[list[str]]:
        lines: list[str] = []
        for symbol, target in target_weights.items():
            current = current_weights.get(symbol, 0.0)
            delta = target - current
            action = "BUY" if delta > 0 else "SELL"
            lines.append(f"{action} {symbol}: adjust {abs(delta) * 100:.2f}% weight")
        return ServiceResult(data=lines, source="Local risk math")

    def get_markowitz_stub(self, expected_returns: dict[str, float], risk_aversion: float = 1.0) -> ServiceResult[dict[str, float]]:
        if not expected_returns:
            return ServiceResult(data=None, error=ErrorEnvelope(code="NOT_FOUND", message="No expected returns supplied.", retriable=False))
        positive = {k: max(0.0, v / max(risk_aversion, 0.1)) for k, v in expected_returns.items()}
        total = sum(positive.values()) or 1.0
        weights = {k: v / total for k, v in positive.items()}
        return ServiceResult(data=weights, source="Local Markowitz-style heuristic")

    def get_dividend_projection(self, annual_dividend_per_share: float, shares: float) -> ServiceResult[dict[str, float]]:
        annual = max(0.0, annual_dividend_per_share) * max(0.0, shares)
        return ServiceResult(data={"annual_dividend_income": annual, "monthly_estimate": annual / 12.0}, source="Local projection")

    def get_tax_estimate(self, realized_gain: float, tax_rate: float) -> ServiceResult[dict[str, float]]:
        tax = max(0.0, realized_gain) * max(0.0, tax_rate)
        return ServiceResult(data={"estimated_tax": tax, "post_tax_gain": realized_gain - tax}, source="Local estimate")


