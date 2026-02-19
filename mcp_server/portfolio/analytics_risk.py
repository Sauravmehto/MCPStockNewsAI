"""Risk, benchmark, and diversification analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd
try:
    from scipy.stats import norm
except ImportError:  # pragma: no cover
    from statistics import NormalDist

    class _NormProxy:
        @staticmethod
        def ppf(value: float) -> float:
            return NormalDist().inv_cdf(value)

    norm = _NormProxy()


def _annualize_volatility(returns: pd.Series) -> float:
    return float(returns.std(ddof=0) * np.sqrt(252))


def _portfolio_returns(weights: np.ndarray, returns_df: pd.DataFrame) -> pd.Series:
    aligned = returns_df.dropna(how="any")
    if aligned.empty:
        return pd.Series(dtype=float)
    return aligned.dot(weights)


def calculate_portfolio_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    joined = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if joined.empty:
        return 0.0
    cov = float(np.cov(joined.iloc[:, 0], joined.iloc[:, 1])[0, 1])
    var = float(np.var(joined.iloc[:, 1]))
    return cov / var if var > 0 else 0.0


def calculate_volatility(portfolio_returns: pd.Series) -> float:
    return _annualize_volatility(portfolio_returns)


def calculate_sharpe_ratio(portfolio_returns: pd.Series, risk_free_rate_annual: float) -> float:
    vol = _annualize_volatility(portfolio_returns)
    if vol <= 0:
        return 0.0
    mean_annual = float(portfolio_returns.mean() * 252)
    return (mean_annual - risk_free_rate_annual) / vol


def calculate_sortino_ratio(portfolio_returns: pd.Series, risk_free_rate_annual: float) -> float:
    downside = portfolio_returns[portfolio_returns < 0]
    downside_std = float(downside.std(ddof=0) * np.sqrt(252)) if len(downside) > 0 else 0.0
    if downside_std <= 0:
        return 0.0
    mean_annual = float(portfolio_returns.mean() * 252)
    return (mean_annual - risk_free_rate_annual) / downside_std


def calculate_max_drawdown(portfolio_returns: pd.Series) -> float:
    if portfolio_returns.empty:
        return 0.0
    cumulative = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    return float(drawdown.min()) * 100.0


def calculate_value_at_risk(portfolio_returns: pd.Series, confidence: float = 0.95, portfolio_value: float = 0.0) -> float:
    if portfolio_returns.empty or portfolio_value <= 0:
        return 0.0
    mu = float(portfolio_returns.mean())
    sigma = float(portfolio_returns.std(ddof=0))
    z = float(norm.ppf(1 - confidence))
    daily_var_return = mu + z * sigma
    return float(daily_var_return * portfolio_value)


def calculate_correlation_matrix(returns_df: pd.DataFrame) -> dict[str, dict[str, float]]:
    corr = returns_df.corr().fillna(0.0)
    return {idx: {col: float(corr.loc[idx, col]) for col in corr.columns} for idx in corr.index}


def calculate_concentration_risk(weights: np.ndarray) -> float:
    # Herfindahl-Hirschman Index scaled to 0-100
    hhi = float(np.sum(np.square(weights)))
    return min(100.0, max(0.0, hhi * 100.0))


def calculate_diversification_score(weights: np.ndarray, returns_df: pd.DataFrame) -> float:
    corr = returns_df.corr().fillna(0.0)
    avg_corr = float(np.mean(np.abs(corr.values)))
    concentration = calculate_concentration_risk(weights) / 100.0
    raw = 100.0 * (1.0 - min(1.0, 0.6 * avg_corr + 0.4 * concentration))
    return max(0.0, min(100.0, raw))


def compare_against_sp500(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> dict[str, float]:
    p_total = float((1 + portfolio_returns.dropna()).prod() - 1) * 100.0 if not portfolio_returns.empty else 0.0
    b_total = float((1 + benchmark_returns.dropna()).prod() - 1) * 100.0 if not benchmark_returns.empty else 0.0
    return {"portfolio_return_percent": p_total, "sp500_return_percent": b_total, "excess_return_percent": p_total - b_total}


def calculate_tracking_error(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    joined = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if joined.empty:
        return 0.0
    diff = joined.iloc[:, 0] - joined.iloc[:, 1]
    return float(diff.std(ddof=0) * np.sqrt(252))


def calculate_information_ratio(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    te = calculate_tracking_error(portfolio_returns, benchmark_returns)
    if te <= 0:
        return 0.0
    joined = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if joined.empty:
        return 0.0
    active_return = float((joined.iloc[:, 0] - joined.iloc[:, 1]).mean() * 252)
    return active_return / te


def build_portfolio_returns(returns_df: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    return _portfolio_returns(weights, returns_df)


