"""Twelve Data adapter with normalized outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode

from mcp_server.providers.http import ProviderError, fetch_json
from mcp_server.providers.models import Interval, NormalizedCandle, NormalizedCompanyProfile, NormalizedNewsItem, NormalizedQuote

TWELVE_BASE_URL = "https://api.twelvedata.com"
TWELVE_INTERVALS: dict[Interval, str] = {
    "1": "1min",
    "5": "5min",
    "15": "15min",
    "30": "30min",
    "60": "1h",
    "D": "1day",
    "W": "1week",
    "M": "1month",
}


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_unix(value: object) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    return None


class TwelveDataClient:
    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _request(self, endpoint: str, params: dict[str, str | int]) -> dict:
        query = dict(params)
        query["apikey"] = self.api_key
        url = f"{TWELVE_BASE_URL}{endpoint}?{urlencode(query)}"
        data = fetch_json(url, provider="twelvedata", timeout_seconds=self.timeout_seconds)
        if isinstance(data, dict) and str(data.get("status", "")).lower() == "error":
            message = str(data.get("message") or "Twelve Data upstream error.")
            lower = message.lower()
            if "rate limit" in lower:
                raise ProviderError("twelvedata", "RATE_LIMIT", message)
            if "api key" in lower or "unauthorized" in lower:
                raise ProviderError("twelvedata", "AUTH", message)
            raise ProviderError("twelvedata", "UPSTREAM", message)
        return data

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        data = self._request("/quote", {"symbol": symbol})
        price = _to_float(data.get("close") or data.get("price"))
        if price is None or price <= 0:
            return None
        change = _to_float(data.get("change")) or 0.0
        percent_change = _to_float(data.get("percent_change")) or 0.0
        high = _to_float(data.get("high")) or price
        low = _to_float(data.get("low")) or price
        open_value = _to_float(data.get("open")) or price
        previous_close = _to_float(data.get("previous_close")) or price
        timestamp = _to_unix(data.get("datetime"))
        return NormalizedQuote(
            symbol=symbol,
            price=price,
            change=change,
            percent_change=percent_change,
            high=high,
            low=low,
            open=open_value,
            previous_close=previous_close,
            timestamp=timestamp,
            source="twelvedata",
        )

    def get_company_profile(self, symbol: str) -> NormalizedCompanyProfile | None:
        data = self._request("/profile", {"symbol": symbol})
        if not isinstance(data, dict):
            return None
        name = data.get("name")
        if not name and not data.get("symbol"):
            return None
        return NormalizedCompanyProfile(
            symbol=symbol,
            name=name if isinstance(name, str) else None,
            exchange=data.get("exchange") if isinstance(data.get("exchange"), str) else None,
            currency=data.get("currency") if isinstance(data.get("currency"), str) else None,
            country=data.get("country") if isinstance(data.get("country"), str) else None,
            industry=data.get("industry") if isinstance(data.get("industry"), str) else None,
            website=data.get("website") if isinstance(data.get("website"), str) else None,
            source="twelvedata",
        )

    def get_candles(self, symbol: str, interval: Interval, from_unix: int, to_unix: int) -> list[NormalizedCandle] | None:
        data = self._request(
            "/time_series",
            {
                "symbol": symbol,
                "interval": TWELVE_INTERVALS[interval],
                "start_date": datetime.fromtimestamp(from_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": datetime.fromtimestamp(to_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "order": "ASC",
                "format": "JSON",
            },
        )
        rows = data.get("values") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return None
        candles: list[NormalizedCandle] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            ts = _to_unix(item.get("datetime"))
            open_value = _to_float(item.get("open"))
            high = _to_float(item.get("high"))
            low = _to_float(item.get("low"))
            close = _to_float(item.get("close"))
            volume = _to_float(item.get("volume")) or 0.0
            if ts is None or open_value is None or high is None or low is None or close is None:
                continue
            candles.append(
                NormalizedCandle(timestamp=ts, open=open_value, high=high, low=low, close=close, volume=volume)
            )
        return candles or None

    def get_news(self, symbol: str, limit: int = 10) -> list[NormalizedNewsItem] | None:
        data = self._request("/news", {"symbol": symbol, "limit": max(1, limit)})
        rows = data if isinstance(data, list) else data.get("news") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return None
        out: list[NormalizedNewsItem] = []
        for item in rows[:limit]:
            if not isinstance(item, dict):
                continue
            out.append(
                NormalizedNewsItem(
                    headline=str(item.get("title") or "Untitled"),
                    summary=item.get("description") if isinstance(item.get("description"), str) else None,
                    url=item.get("url") if isinstance(item.get("url"), str) else None,
                    source=item.get("source") if isinstance(item.get("source"), str) else "Twelve Data",
                    datetime=_to_unix(item.get("datetime")),
                )
            )
        return out or None


