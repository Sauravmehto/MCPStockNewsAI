import pandas as pd

from mcp_server.portfolio.analytics_risk import (
    calculate_information_ratio,
    calculate_portfolio_beta,
    calculate_tracking_error,
    calculate_value_at_risk,
)


def test_portfolio_risk_metrics() -> None:
    portfolio_returns = pd.Series([0.01, -0.005, 0.007, 0.002, -0.001])
    benchmark_returns = pd.Series([0.008, -0.004, 0.006, 0.001, -0.002])
    beta = calculate_portfolio_beta(portfolio_returns, benchmark_returns)
    te = calculate_tracking_error(portfolio_returns, benchmark_returns)
    ir = calculate_information_ratio(portfolio_returns, benchmark_returns)
    var95 = calculate_value_at_risk(portfolio_returns, confidence=0.95, portfolio_value=100000)
    assert isinstance(beta, float)
    assert te >= 0
    assert isinstance(ir, float)
    assert isinstance(var95, float)


