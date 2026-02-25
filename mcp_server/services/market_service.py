"""Market-domain service."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from mcp_server.providers.fred import FredClient
from mcp_server.services.base import ServiceContext, ServiceResult
from mcp_server.services.stock_service import StockService


class MarketService:
    def __init__(self, ctx: ServiceContext, stocks: StockService) -> None:
        self.ctx = ctx
        self.stocks = stocks

    def _fred(self) -> FredClient | None:
        c = self.ctx.get_provider("fred")
        return c if isinstance(c, FredClient) else None

    def get_market_status(self) -> ServiceResult[dict[str, str]]:
        hour = time.gmtime().tm_hour
        status = "open-ish" if 14 <= hour <= 21 else "closed-ish"
        return ServiceResult(
            data={"status": status, "timezone": "UTC", "note": "Heuristic market-hours estimate"},
            fetched_at=time.time(),
            data_provider="Market heuristic",
            data_license="Internal heuristic",
        )

    def get_market_hours(self) -> ServiceResult[dict[str, object]]:
        now = datetime.now(timezone.utc)
        weekday = now.weekday()
        is_weekend = weekday >= 5
        status = "closed" if is_weekend else ("open" if 14 <= now.hour <= 21 else "closed")
        next_open = "14:30:00Z"
        next_close = "21:00:00Z"
        holidays = ["2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03"]
        return ServiceResult(
            data={
                "status": status,
                "timezone": "UTC",
                "next_open_time_utc": next_open,
                "next_close_time_utc": next_close,
                "holiday_schedule": holidays,
            },
            source="Market hours heuristic",
            fetched_at=time.time(),
            data_provider="Market hours heuristic",
            data_license="Internal heuristic",
        )

    def get_indices(self) -> ServiceResult[list[dict[str, float | str]]]:
        mapping = [("S&P 500", "SPY"), ("NASDAQ 100", "QQQ"), ("Dow Jones", "DIA")]
        lines: list[dict[str, float | str]] = []
        source = None
        for name, symbol in mapping:
            quote = self.stocks.get_quote(symbol)
            if quote.data:
                source = source or quote.source
                lines.append({"name": name, "symbol": symbol, "price": quote.data.price, "change_pct": quote.data.percent_change})
        return ServiceResult(data=lines, source=source)

    def get_vix(self) -> ServiceResult[dict[str, str]]:
        fred = self._fred()
        if not fred:
            return ServiceResult(data=None, error=None, warning="FRED key not configured")
        observations = fred.get_series("VIXCLS", limit=1)
        if not observations:
            return ServiceResult(data=None, error=None, warning="No VIX observation returned")
        return ServiceResult(data=observations[0], source="FRED")

    def get_movers(self, kind: str = "gainers") -> ServiceResult[list[str]]:
        sample = {
            "gainers": ["NVDA", "AMD", "META"],
            "losers": ["TSLA", "PFE", "NKE"],
            "active": ["AAPL", "TSLA", "NVDA"],
        }
        return ServiceResult(data=sample.get(kind, sample["active"]), source="Heuristic sample")

    def get_sector_performance(self) -> ServiceResult[list[dict[str, str | float]]]:
        sectors = [
            {"sector": "Technology", "change_pct": 0.8},
            {"sector": "Financials", "change_pct": -0.2},
            {"sector": "Healthcare", "change_pct": 0.1},
        ]
        return ServiceResult(data=sectors, source="Heuristic sample")

    def get_market_breadth(self) -> ServiceResult[dict[str, int]]:
        return ServiceResult(data={"advancers": 310, "decliners": 185, "unchanged": 45}, source="Heuristic sample")

    def get_economic_calendar(self, days_ahead: int = 7) -> ServiceResult[list[dict[str, str]]]:
        bounded = max(1, min(days_ahead, 30))
        sample = [
            {"event": "FOMC Meeting", "date": "2026-03-18", "importance": "high"},
            {"event": "US CPI", "date": "2026-03-12", "importance": "high"},
            {"event": "US Non-Farm Payrolls", "date": "2026-03-06", "importance": "high"},
            {"event": "Major earnings window", "date": "2026-03-10", "importance": "medium"},
        ]
        return ServiceResult(
            data=sample[: min(len(sample), max(1, bounded // 2 + 1))],
            source="Economic calendar heuristic",
            fetched_at=time.time(),
            data_provider="Economic calendar heuristic",
            data_license="Internal heuristic",
        )


