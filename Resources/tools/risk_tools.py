"""Risk-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response
from mcp_server.services.base import validate_interval, validate_range, validate_symbol
from mcp_server.tools.common import ensure_data

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_risk_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get beta versus benchmark.")
    def get_beta(symbol: str, benchmark_symbol: str, interval: str, from_unix: int, to_unix: int) -> str:
        symbol = validate_symbol(symbol)
        benchmark_symbol = validate_symbol(benchmark_symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.risk.get_beta(symbol, benchmark_symbol, interval, from_unix, to_unix)
        payload = ensure_data(result.data, result.error)
        return format_response(title=f"Beta for {symbol}", source=result.source, warning=result.warning, lines=[f"beta: {payload['beta']:.6f}"])

    @mcp.tool(description="Get Sharpe and Sortino ratios.")
    def get_sharpe_sortino(symbol: str, interval: str, from_unix: int, to_unix: int, riskFreeRate: float = 0.0) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.risk.get_sharpe_sortino(symbol, interval, from_unix, to_unix, risk_free_rate=riskFreeRate)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Sharpe/Sortino for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"sharpe: {payload['sharpe']:.6f}", f"sortino: {payload['sortino']:.6f}"],
        )

    @mcp.tool(description="Get max drawdown.")
    def get_max_drawdown(symbol: str, interval: str, from_unix: int, to_unix: int) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.risk.get_max_drawdown(symbol, interval, from_unix, to_unix)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Max drawdown for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"max_drawdown: {payload['max_drawdown']:.6f}"],
        )

    @mcp.tool(description="Get Value at Risk (historical).")
    def get_var(symbol: str, interval: str, from_unix: int, to_unix: int, confidence: float = 0.95) -> str:
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.risk.get_var(symbol, interval, from_unix, to_unix, confidence=confidence)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"VaR for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"value_at_risk: {payload['value_at_risk']:.6f}", f"confidence: {payload['confidence']:.2f}"],
        )

    @mcp.tool(description="Get correlation between two symbols.")
    def get_correlation(symbol: str, peer_symbol: str, interval: str, from_unix: int, to_unix: int) -> str:
        symbol = validate_symbol(symbol)
        peer_symbol = validate_symbol(peer_symbol)
        interval = validate_interval(interval)
        validate_range(from_unix, to_unix)
        result = services.risk.get_correlation(symbol, peer_symbol, interval, from_unix, to_unix)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title=f"Correlation: {symbol} vs {peer_symbol}",
            source=result.source,
            warning=result.warning,
            lines=[f"correlation: {payload['correlation']:.6f}"],
        )

    @mcp.tool(description="Get rebalance recommendations from current/target weights.")
    def get_rebalance_plan(currentWeights: dict[str, float], targetWeights: dict[str, float]) -> str:
        result = services.risk.get_rebalance_plan(currentWeights, targetWeights)
        rows = ensure_data(result.data, result.error)
        return format_response("Rebalance plan", rows, source=result.source, warning=result.warning)

    @mcp.tool(description="Compute Markowitz-style heuristic allocation from expected returns.")
    def get_markowitz_allocation(expectedReturns: dict[str, float], riskAversion: float = 1.0) -> str:
        result = services.risk.get_markowitz_stub(expectedReturns, risk_aversion=riskAversion)
        payload = ensure_data(result.data, result.error)
        lines = [f"{symbol}: {weight:.4f}" for symbol, weight in payload.items()]
        return format_response("Markowitz-style allocation", lines, source=result.source, warning=result.warning)

    @mcp.tool(description="Estimate dividend income projection.")
    def get_dividend_projection(annualDividendPerShare: float, shares: float) -> str:
        result = services.risk.get_dividend_projection(annualDividendPerShare, shares)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title="Dividend projection",
            source=result.source,
            warning=result.warning,
            lines=[f"annual_dividend_income: {payload['annual_dividend_income']:.2f}", f"monthly_estimate: {payload['monthly_estimate']:.2f}"],
        )

    @mcp.tool(description="Estimate tax impact from realized gain.")
    def get_tax_estimate(realizedGain: float, taxRate: float) -> str:
        result = services.risk.get_tax_estimate(realizedGain, taxRate)
        payload = ensure_data(result.data, result.error)
        return format_response(
            title="Tax estimate",
            source=result.source,
            warning=result.warning,
            lines=[f"estimated_tax: {payload['estimated_tax']:.2f}", f"post_tax_gain: {payload['post_tax_gain']:.2f}"],
        )


