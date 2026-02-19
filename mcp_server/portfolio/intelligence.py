"""Portfolio scoring and summary generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioScores:
    portfolio_risk_score: float
    diversification_score: float
    allocation_efficiency_score: float
    bucket_health_score: float


def compute_scores(
    beta: float,
    volatility: float,
    max_drawdown_percent: float,
    diversification_score: float,
    overweight_count: int,
    underweight_count: int,
    bucket_imbalance_count: int,
) -> PortfolioScores:
    risk_raw = 40 * min(2.0, abs(beta)) / 2.0 + 35 * min(0.6, volatility) / 0.6 + 25 * min(60.0, abs(max_drawdown_percent)) / 60.0
    risk_score = max(0.0, min(100.0, risk_raw))
    alloc_eff = max(0.0, 100.0 - 10.0 * (overweight_count + underweight_count))
    bucket_health = max(0.0, 100.0 - 15.0 * bucket_imbalance_count)
    return PortfolioScores(
        portfolio_risk_score=risk_score,
        diversification_score=max(0.0, min(100.0, diversification_score)),
        allocation_efficiency_score=alloc_eff,
        bucket_health_score=bucket_health,
    )


def generate_fallback_summary(
    risk_score: float,
    beta: float,
    diversification_score: float,
    benchmark_excess_return: float,
    sector_concentration: list[dict[str, float | str]],
    overweight_positions: list[dict[str, float | str]],
) -> str:
    risk_level = "high" if risk_score >= 70 else "moderate" if risk_score >= 40 else "low"
    tilt = "growth/aggressive" if beta > 1.1 else "defensive" if beta < 0.9 else "balanced"
    concentration_note = (
        "Sector concentration risk detected."
        if sector_concentration
        else "Sector exposure appears reasonably distributed."
    )
    benchmark_note = (
        f"Portfolio is outperforming SP500 by {benchmark_excess_return:.2f}%."
        if benchmark_excess_return > 0
        else f"Portfolio is underperforming SP500 by {abs(benchmark_excess_return):.2f}%."
    )
    improve = (
        "Trim overweight positions and rebalance target weights."
        if overweight_positions
        else "Maintain discipline and monitor drift against targets."
    )
    return (
        f"Portfolio risk is {risk_level} (score {risk_score:.1f}/100) with a {tilt} tilt (beta {beta:.2f}). "
        f"Diversification score is {diversification_score:.1f}/100. {concentration_note} "
        f"{benchmark_note} Suggested improvement: {improve}"
    )


