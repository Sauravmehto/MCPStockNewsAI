"""Market-domain service."""

from __future__ import annotations

import time

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
        return ServiceResult(data={"status": status, "timezone": "UTC", "note": "Heuristic market-hours estimate"})

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


