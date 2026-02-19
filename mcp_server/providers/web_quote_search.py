"""Web quote fallback provider for last-resort stock price lookups."""

from __future__ import annotations

from urllib.parse import quote_plus

from mcp_server.providers.http import fetch_json
from mcp_server.providers.models import NormalizedQuote


class WebQuoteSearchClient:
    """Fallback that uses public web quote endpoints when API providers fail."""

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        encoded = quote_plus(symbol)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={encoded}"
        data = fetch_json(url, provider="websearch", timeout_seconds=self.timeout_seconds)
        rows = ((data or {}).get("quoteResponse") or {}).get("result") or []
        if not rows:
            return None
        item = rows[0] if isinstance(rows[0], dict) else None
        if not item:
            return None
        price = item.get("regularMarketPrice")
        if not isinstance(price, (int, float)) or price <= 0:
            return None
        previous_close = item.get("regularMarketPreviousClose")
        prev = float(previous_close) if isinstance(previous_close, (int, float)) and previous_close > 0 else float(price)
        return NormalizedQuote(
            symbol=symbol,
            price=float(price),
            change=float(item.get("regularMarketChange") or 0.0),
            percent_change=float(item.get("regularMarketChangePercent") or 0.0),
            high=float(item.get("regularMarketDayHigh") or price),
            low=float(item.get("regularMarketDayLow") or price),
            open=float(item.get("regularMarketOpen") or price),
            previous_close=prev,
            timestamp=int(item["regularMarketTime"]) if isinstance(item.get("regularMarketTime"), int) else None,
            source="websearch",
        )


