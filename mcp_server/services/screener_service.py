"""Stateless screener service."""

from __future__ import annotations

from mcp_server.services.base import ServiceResult
from mcp_server.services.stock_service import StockService


class ScreenerService:
    def __init__(self, stocks: StockService) -> None:
        self.stocks = stocks

    def screen(
        self,
        symbols: list[str],
        min_price: float | None = None,
        max_price: float | None = None,
        sector_hint: str | None = None,
    ) -> ServiceResult[list[str]]:
        lines: list[str] = []
        for symbol in symbols:
            quote = self.stocks.get_quote(symbol)
            if not quote.data:
                continue
            if min_price is not None and quote.data.price < min_price:
                continue
            if max_price is not None and quote.data.price > max_price:
                continue
            profile = self.stocks.get_profile(symbol)
            if sector_hint and profile.data and profile.data.industry:
                if sector_hint.lower() not in profile.data.industry.lower():
                    continue
            lines.append(
                f"{symbol}: ${quote.data.price:.2f}"
                + (f" | industry={profile.data.industry}" if profile.data and profile.data.industry else "")
            )
        return ServiceResult(data=lines, source="Stock service filter")


