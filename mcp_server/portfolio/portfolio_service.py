"""Portfolio analytics orchestration service."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import numpy as np
import pandas as pd
try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None

from mcp_server.portfolio.analytics_core import (
    calculate_bucket_distribution,
    calculate_capital_distribution,
    calculate_contribution_to_return,
    calculate_current_allocation_percent,
    calculate_sector_exposure,
    calculate_total_portfolio_value,
    calculate_total_return_percent,
    calculate_unrealized_pnl,
    calculate_weighted_average_cost,
    compare_target_vs_actual_allocation,
    detect_bucket_imbalance,
    detect_overweight_positions,
    detect_sector_concentration,
    detect_underweight_positions,
    enrich_with_market_values,
)
from mcp_server.portfolio.analytics_risk import (
    build_portfolio_returns,
    calculate_concentration_risk,
    calculate_correlation_matrix,
    calculate_diversification_score,
    calculate_information_ratio,
    calculate_max_drawdown,
    calculate_portfolio_beta,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_tracking_error,
    calculate_value_at_risk,
    calculate_volatility,
    compare_against_sp500,
)
from mcp_server.portfolio.analytics_stress import (
    simulate_defensive_outperformance,
    simulate_growth_selloff,
    simulate_market_drop_20_percent,
    simulate_volatility_spike,
)
from mcp_server.portfolio.data_loader import load_portfolio_excel
from mcp_server.portfolio.intelligence import compute_scores, generate_fallback_summary
from mcp_server.portfolio.validation import validate_portfolio_frame
from mcp_server.providers.anthropic_client import AnthropicClient
from mcp_server.providers.fred import FredClient
from mcp_server.services.base import ServiceContext


def _json_validation_error(errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {"ok": False, "error": {"type": "validation_error", "errors": errors}}


class PortfolioService:
    def __init__(
        self,
        ctx: ServiceContext,
        enable_ai_summary: bool = True,
        resource_updated_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.ctx = ctx
        self.enable_ai_summary = enable_ai_summary
        self._current_resource_cache_key = "portfolio:current_resource"
        self._resource_snapshot_prefix = "portfolio:resource_snapshot:"
        self._resource_updated_callback = resource_updated_callback

    def _store_current_resource_snapshot(
        self,
        report_type: str,
        source_file_path: str,
        payload: dict[str, Any],
    ) -> None:
        snapshot = {
            "uri": "portfolio://current",
            "report_type": report_type,
            "source_file_path": source_file_path,
            "payload": payload,
        }
        self.ctx.cache.set(self._current_resource_cache_key, snapshot, ttl_seconds=self.ctx.cache_ttl_seconds)
        self.ctx.cache.set(
            f"{self._resource_snapshot_prefix}{report_type}",
            snapshot,
            ttl_seconds=self.ctx.cache_ttl_seconds,
        )
        if self._resource_updated_callback is not None:
            self._resource_updated_callback("portfolio://current")

    def get_current_resource_snapshot(self) -> dict[str, Any] | None:
        cached = self.ctx.cache.get(self._current_resource_cache_key)
        return cached if isinstance(cached, dict) else None

    def get_resource_snapshot(self, report_type: str) -> dict[str, Any] | None:
        normalized = report_type.strip().lower()
        if normalized not in {"analysis", "benchmark", "stress_test"}:
            return None
        cached = self.ctx.cache.get(f"{self._resource_snapshot_prefix}{normalized}")
        return cached if isinstance(cached, dict) else None

    def _fred(self) -> FredClient | None:
        provider = self.ctx.get_provider("fred")
        return provider if isinstance(provider, FredClient) else None

    def _anthropic(self) -> AnthropicClient | None:
        provider = self.ctx.get_provider("anthropic")
        return provider if isinstance(provider, AnthropicClient) else None

    async def _fetch_latest_close(self, symbol: str) -> float | None:
        cache_key = f"portfolio:price:{symbol}"
        cached = self.ctx.cache.get(cache_key)
        if isinstance(cached, (int, float)):
            return float(cached)

        def _call() -> float | None:
            if yf is None:
                return None
            history = yf.Ticker(symbol).history(period="5d")
            if history.empty or "Close" not in history:
                return None
            value = float(history["Close"].dropna().iloc[-1])
            return value if value > 0 else None

        value = await asyncio.to_thread(_call)
        if value is not None:
            self.ctx.cache.set(cache_key, value, ttl_seconds=self.ctx.cache_ttl_seconds)
        return value

    async def _fetch_history_close(self, symbol: str) -> pd.Series:
        cache_key = f"portfolio:history:{symbol}:1y"
        cached = self.ctx.cache.get(cache_key)
        if isinstance(cached, list):
            return pd.Series(cached, name=symbol)

        def _call() -> pd.Series:
            if yf is None:
                return pd.Series(dtype=float, name=symbol)
            data = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=True)
            if data.empty or "Close" not in data:
                return pd.Series(dtype=float, name=symbol)
            return data["Close"].dropna().rename(symbol)

        series = await asyncio.to_thread(_call)
        if not series.empty:
            self.ctx.cache.set(cache_key, series.tolist(), ttl_seconds=self.ctx.cache_ttl_seconds)
        return series

    async def _fetch_sector(self, symbol: str) -> str:
        cache_key = f"portfolio:sector:{symbol}"
        cached = self.ctx.cache.get(cache_key)
        if isinstance(cached, str):
            return cached

        def _call() -> str:
            if yf is None:
                return "Unknown"
            info = yf.Ticker(symbol).info
            sector = info.get("sector") if isinstance(info, dict) else None
            return str(sector) if sector else "Unknown"

        sector = await asyncio.to_thread(_call)
        self.ctx.cache.set(cache_key, sector, ttl_seconds=self.ctx.cache_ttl_seconds)
        return sector

    def _risk_free_rate(self) -> float:
        fred = self._fred()
        if not fred:
            return 0.0
        series = fred.get_series("DGS10", limit=5) or []
        for row in series:
            try:
                value = float(row["value"])
            except (ValueError, KeyError):
                continue
            if value > 0:
                return value / 100.0
        return 0.0

    async def _collect_market_data(self, symbols: list[str]) -> tuple[dict[str, float], pd.DataFrame, dict[str, str], pd.Series]:
        price_tasks = [self._fetch_latest_close(symbol) for symbol in symbols]
        history_tasks = [self._fetch_history_close(symbol) for symbol in symbols]
        sector_tasks = [self._fetch_sector(symbol) for symbol in symbols]
        benchmark_task = self._fetch_history_close("SPY")

        prices = await asyncio.gather(*price_tasks)
        histories = await asyncio.gather(*history_tasks)
        sectors = await asyncio.gather(*sector_tasks)
        benchmark = await benchmark_task

        price_map = {symbol: price for symbol, price in zip(symbols, prices) if isinstance(price, (int, float))}
        sector_map = {symbol: sector for symbol, sector in zip(symbols, sectors)}
        close_df = pd.concat(histories, axis=1) if histories else pd.DataFrame()
        return price_map, close_df, sector_map, benchmark

    def validate_excel(self, file_path: str) -> dict[str, Any]:
        try:
            frame = load_portfolio_excel(file_path)
        except Exception as error:
            return _json_validation_error([{"field": "file_path", "message": str(error), "code": "file_error"}])
        issues = validate_portfolio_frame(frame)
        if issues:
            return _json_validation_error(
                [
                    {"field": issue.field, "message": issue.message, "row": issue.row, "code": issue.code}
                    for issue in issues
                ]
            )
        return {"ok": True, "message": "Portfolio file validated.", "rows": int(len(frame))}

    def _normalize_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()
        data["Symbol"] = data["Symbol"].astype(str).str.upper().str.strip()
        data["Bucket"] = data["Bucket"].astype(str).str.strip()
        data["Quantity"] = data["Quantity"].astype(int)
        data["Entry_Price"] = data["Entry_Price"].astype(float)
        data["Target_Weight"] = data["Target_Weight"].astype(float)
        return data

    async def analyze_excel_async(self, file_path: str, include_ai_summary: bool = True) -> dict[str, Any]:
        validation = self.validate_excel(file_path)
        if not validation.get("ok"):
            return validation

        frame = self._normalize_frame(load_portfolio_excel(file_path))
        symbols = sorted(frame["Symbol"].unique().tolist())
        price_map, close_df, sector_map, benchmark_close = await self._collect_market_data(symbols)

        missing_symbols = [symbol for symbol in symbols if symbol not in price_map]
        if missing_symbols:
            return _json_validation_error(
                [
                    {
                        "field": "Symbol",
                        "code": "invalid_symbol",
                        "message": f"No market data found for symbol: {symbol}",
                    }
                    for symbol in missing_symbols
                ]
            )

        enriched = enrich_with_market_values(frame, price_map)
        portfolio_value = calculate_total_portfolio_value(enriched)
        unrealized_pnl = calculate_unrealized_pnl(enriched)
        total_return_percent = calculate_total_return_percent(enriched)
        current_alloc = calculate_current_allocation_percent(enriched)
        weighted_cost = calculate_weighted_average_cost(enriched)
        contribution_to_return = calculate_contribution_to_return(enriched)
        bucket_distribution = calculate_bucket_distribution(enriched)
        target_vs_actual = compare_target_vs_actual_allocation(enriched)
        overweight = detect_overweight_positions(enriched)
        underweight = detect_underweight_positions(enriched)
        bucket_imbalance = detect_bucket_imbalance(enriched)
        capital_distribution = calculate_capital_distribution(enriched)

        aligned_prices = close_df.dropna(how="any")
        returns_df = aligned_prices.pct_change().dropna() if not aligned_prices.empty else pd.DataFrame()
        symbol_weights = enriched.groupby("Symbol")["Market_Value"].sum()
        symbol_weights = symbol_weights / symbol_weights.sum() if symbol_weights.sum() else symbol_weights
        weights = np.array([float(symbol_weights.get(symbol, 0.0)) for symbol in returns_df.columns], dtype=float)
        portfolio_returns = build_portfolio_returns(returns_df, weights) if not returns_df.empty else pd.Series(dtype=float)
        benchmark_returns = benchmark_close.pct_change().dropna() if not benchmark_close.empty else pd.Series(dtype=float)

        risk_free_rate = self._risk_free_rate()
        beta = calculate_portfolio_beta(portfolio_returns, benchmark_returns)
        volatility = calculate_volatility(portfolio_returns)
        sharpe = calculate_sharpe_ratio(portfolio_returns, risk_free_rate)
        sortino = calculate_sortino_ratio(portfolio_returns, risk_free_rate)
        max_drawdown = calculate_max_drawdown(portfolio_returns)
        var95 = calculate_value_at_risk(portfolio_returns, 0.95, portfolio_value)
        correlation_matrix = calculate_correlation_matrix(returns_df) if not returns_df.empty else {}
        concentration_risk = calculate_concentration_risk(weights) if len(weights) else 0.0
        diversification_score = calculate_diversification_score(weights, returns_df) if len(weights) else 0.0

        benchmark_comparison = compare_against_sp500(portfolio_returns, benchmark_returns)
        tracking_error = calculate_tracking_error(portfolio_returns, benchmark_returns)
        information_ratio = calculate_information_ratio(portfolio_returns, benchmark_returns)
        benchmark_comparison["tracking_error"] = tracking_error
        benchmark_comparison["information_ratio"] = information_ratio

        sector_exposure = calculate_sector_exposure(sector_map, enriched)
        sector_concentration = detect_sector_concentration(sector_exposure)

        stress_tests = {
            "market_drop_20_percent": simulate_market_drop_20_percent(enriched),
            "growth_selloff": simulate_growth_selloff(enriched),
            "defensive_outperformance": simulate_defensive_outperformance(enriched),
            "volatility_spike": simulate_volatility_spike(enriched),
        }

        scores = compute_scores(
            beta=beta,
            volatility=volatility,
            max_drawdown_percent=max_drawdown,
            diversification_score=diversification_score,
            overweight_count=len(overweight),
            underweight_count=len(underweight),
            bucket_imbalance_count=len(bucket_imbalance),
        )

        ai_summary = generate_fallback_summary(
            risk_score=scores.portfolio_risk_score,
            beta=beta,
            diversification_score=scores.diversification_score,
            benchmark_excess_return=benchmark_comparison["excess_return_percent"],
            sector_concentration=sector_concentration,
            overweight_positions=overweight,
        )
        if include_ai_summary and self.enable_ai_summary:
            anthropic = self._anthropic()
            if anthropic:
                summary_payload = {
                    "risk_score": scores.portfolio_risk_score,
                    "beta": beta,
                    "volatility": volatility,
                    "diversification_score": scores.diversification_score,
                    "benchmark": benchmark_comparison,
                    "sector_concentration": sector_concentration,
                    "overweight": overweight,
                    "underweight": underweight,
                }
                prompt = (
                    "You are an institutional portfolio risk analyst. "
                    "Create an executive summary in 5-8 sentences using this payload: "
                    f"{json.dumps(summary_payload, default=str)}"
                )
                try:
                    model_summary = anthropic.generate_summary(prompt)
                    if model_summary:
                        ai_summary = model_summary
                except Exception:
                    pass

        return {
            "ok": True,
            "portfolio_value": portfolio_value,
            "total_unrealized_pnl": unrealized_pnl,
            "total_return_percent": total_return_percent,
            "weighted_average_cost": weighted_cost,
            "allocation": current_alloc,
            "target_vs_actual": target_vs_actual,
            "contribution_to_return": contribution_to_return,
            "bucket_distribution": bucket_distribution,
            "bucket_imbalance": bucket_imbalance,
            "overweight_positions": overweight,
            "underweight_positions": underweight,
            "capital_distribution": capital_distribution,
            "beta": beta,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_drawdown,
            "value_at_risk_95": var95,
            "correlation_matrix": correlation_matrix,
            "concentration_risk": concentration_risk,
            "diversification_score": scores.diversification_score,
            "risk_score": scores.portfolio_risk_score,
            "allocation_efficiency_score": scores.allocation_efficiency_score,
            "bucket_health_score": scores.bucket_health_score,
            "benchmark_comparison": benchmark_comparison,
            "sector_exposure": sector_exposure,
            "sector_concentration": sector_concentration,
            "stress_tests": stress_tests,
            "ai_summary": ai_summary,
        }

    def analyze_excel(self, file_path: str, include_ai_summary: bool = True) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            payload = asyncio.run(self.analyze_excel_async(file_path, include_ai_summary=include_ai_summary))
            if payload.get("ok"):
                self._store_current_resource_snapshot("analysis", file_path, payload)
            return payload
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                lambda: asyncio.run(self.analyze_excel_async(file_path, include_ai_summary=include_ai_summary))
            )
            payload = future.result()
            if payload.get("ok"):
                self._store_current_resource_snapshot("analysis", file_path, payload)
            return payload

    def benchmark_report(self, file_path: str) -> dict[str, Any]:
        payload = self.analyze_excel(file_path, include_ai_summary=False)
        if not payload.get("ok"):
            return payload
        benchmark_payload = {
            "ok": True,
            "benchmark_comparison": payload["benchmark_comparison"],
            "beta": payload["beta"],
            "tracking_error": payload["benchmark_comparison"]["tracking_error"],
            "information_ratio": payload["benchmark_comparison"]["information_ratio"],
        }
        self._store_current_resource_snapshot("benchmark", file_path, benchmark_payload)
        return benchmark_payload

    def stress_test(self, file_path: str) -> dict[str, Any]:
        payload = self.analyze_excel(file_path, include_ai_summary=False)
        if not payload.get("ok"):
            return payload
        stress_payload = {"ok": True, "portfolio_value": payload["portfolio_value"], "stress_tests": payload["stress_tests"]}
        self._store_current_resource_snapshot("stress_test", file_path, stress_payload)
        return stress_payload


