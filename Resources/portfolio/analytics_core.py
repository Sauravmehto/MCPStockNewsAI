"""Core and allocation portfolio analytics."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd


def enrich_with_market_values(frame: pd.DataFrame, live_prices: dict[str, float]) -> pd.DataFrame:
    data = frame.copy()
    data["Symbol"] = data["Symbol"].astype(str).str.upper().str.strip()
    data["Live_Price"] = data["Symbol"].map(live_prices).astype(float)
    data["Market_Value"] = data["Quantity"].astype(float) * data["Live_Price"]
    data["Cost_Basis"] = data["Quantity"].astype(float) * data["Entry_Price"].astype(float)
    data["PnL"] = data["Market_Value"] - data["Cost_Basis"]
    portfolio_value = float(data["Market_Value"].sum()) or 1.0
    data["Current_Allocation"] = data["Market_Value"] / portfolio_value
    data["Contribution_To_Return"] = data["PnL"] / portfolio_value
    return data


def calculate_total_portfolio_value(frame: pd.DataFrame) -> float:
    return float(frame["Market_Value"].sum())


def calculate_unrealized_pnl(frame: pd.DataFrame) -> float:
    return float(frame["PnL"].sum())


def calculate_total_return_percent(frame: pd.DataFrame) -> float:
    cost = float(frame["Cost_Basis"].sum())
    if cost <= 0:
        return 0.0
    return (float(frame["PnL"].sum()) / cost) * 100.0


def calculate_current_allocation_percent(frame: pd.DataFrame) -> dict[str, float]:
    return {row.Symbol: float(row.Current_Allocation) for row in frame.itertuples(index=False)}


def calculate_weighted_average_cost(frame: pd.DataFrame) -> float:
    total_qty = float(frame["Quantity"].sum())
    if total_qty <= 0:
        return 0.0
    return float((frame["Entry_Price"] * frame["Quantity"]).sum() / total_qty)


def calculate_contribution_to_return(frame: pd.DataFrame) -> dict[str, float]:
    return {row.Symbol: float(row.Contribution_To_Return) for row in frame.itertuples(index=False)}


def calculate_bucket_distribution(frame: pd.DataFrame) -> dict[str, float]:
    totals = frame.groupby("Bucket")["Market_Value"].sum()
    portfolio_value = float(frame["Market_Value"].sum()) or 1.0
    return {bucket: float(value / portfolio_value) for bucket, value in totals.to_dict().items()}


def compare_target_vs_actual_allocation(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for row in frame.itertuples(index=False):
        out[row.Symbol] = {
            "target": float(row.Target_Weight),
            "actual": float(row.Current_Allocation),
            "delta": float(row.Current_Allocation - row.Target_Weight),
        }
    return out


def detect_overweight_positions(frame: pd.DataFrame, threshold: float = 0.02) -> list[dict[str, float | str]]:
    results: list[dict[str, float | str]] = []
    for row in frame.itertuples(index=False):
        delta = float(row.Current_Allocation - row.Target_Weight)
        if delta > threshold:
            results.append({"symbol": row.Symbol, "delta": delta})
    return results


def detect_underweight_positions(frame: pd.DataFrame, threshold: float = 0.02) -> list[dict[str, float | str]]:
    results: list[dict[str, float | str]] = []
    for row in frame.itertuples(index=False):
        delta = float(row.Current_Allocation - row.Target_Weight)
        if delta < -threshold:
            results.append({"symbol": row.Symbol, "delta": delta})
    return results


def detect_bucket_imbalance(frame: pd.DataFrame, threshold: float = 0.1) -> list[dict[str, float | str]]:
    actual = frame.groupby("Bucket")["Current_Allocation"].sum().to_dict()
    target = frame.groupby("Bucket")["Target_Weight"].sum().to_dict()
    imbalances: list[dict[str, float | str]] = []
    for bucket in sorted(set(actual) | set(target)):
        delta = float(actual.get(bucket, 0.0) - target.get(bucket, 0.0))
        if abs(delta) > threshold:
            imbalances.append({"bucket": bucket, "delta": delta})
    return imbalances


def calculate_capital_distribution(frame: pd.DataFrame) -> dict[str, float]:
    return {row.Symbol: float(row.Market_Value) for row in frame.itertuples(index=False)}


def calculate_sector_exposure(sector_map: dict[str, str], frame: pd.DataFrame) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    total_value = float(frame["Market_Value"].sum()) or 1.0
    for row in frame.itertuples(index=False):
        sector = sector_map.get(row.Symbol, "Unknown")
        totals[sector] += float(row.Market_Value)
    return {sector: value / total_value for sector, value in totals.items()}


def detect_sector_concentration(sector_exposure: dict[str, float], threshold: float = 0.3) -> list[dict[str, float | str]]:
    return [{"sector": sector, "weight": weight} for sector, weight in sector_exposure.items() if weight >= threshold]


