"""Portfolio stress-testing scenarios."""

from __future__ import annotations

import pandas as pd


def _scenario_pnl(frame: pd.DataFrame, shock_by_symbol: dict[str, float]) -> dict[str, float]:
    base_value = float(frame["Market_Value"].sum())
    shocked = 0.0
    for row in frame.itertuples(index=False):
        shock = shock_by_symbol.get(row.Symbol, 0.0)
        shocked += float(row.Market_Value) * (1.0 + shock)
    pnl = shocked - base_value
    return {
        "base_value": base_value,
        "stressed_value": shocked,
        "pnl": pnl,
        "pnl_percent": (pnl / base_value * 100.0) if base_value > 0 else 0.0,
    }


def simulate_market_drop_20_percent(frame: pd.DataFrame) -> dict[str, float]:
    return _scenario_pnl(frame, {row.Symbol: -0.2 for row in frame.itertuples(index=False)})


def simulate_growth_selloff(frame: pd.DataFrame) -> dict[str, float]:
    shocks: dict[str, float] = {}
    for row in frame.itertuples(index=False):
        shocks[row.Symbol] = -0.3 if row.Bucket == "Growth" else -0.1
    return _scenario_pnl(frame, shocks)


def simulate_defensive_outperformance(frame: pd.DataFrame) -> dict[str, float]:
    shocks: dict[str, float] = {}
    for row in frame.itertuples(index=False):
        shocks[row.Symbol] = 0.1 if row.Bucket == "Defensive" else -0.05
    return _scenario_pnl(frame, shocks)


def simulate_volatility_spike(frame: pd.DataFrame) -> dict[str, float]:
    shocks: dict[str, float] = {}
    for row in frame.itertuples(index=False):
        shocks[row.Symbol] = -0.2 if row.Bucket in {"Speculative", "Growth"} else -0.08
    return _scenario_pnl(frame, shocks)


