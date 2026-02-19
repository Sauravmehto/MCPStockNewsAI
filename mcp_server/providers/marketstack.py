"""MarketStack adapter with normalized outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode

from mcp_server.providers.http import ProviderError, fetch_json
from mcp_server.providers.models import Interval, NormalizedCandle, NormalizedQuote

MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1"
MARKETSTACK_INTERVALS: dict[Interval, str] = {
    "1": "1min",
    "5": "5min",
    "15": "15min",
    "30": "30min",
    "60": "1hour",
    "D": "24hour",
    "W": "24hour",
    "M": "24hour",
}


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_unix(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    clean = value.replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(clean).timestamp())
    except ValueError:
        return None


class MarketStackClient:
    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _request(self, endpoint: str, params: dict[str, str | int]) -> dict:
        query = dict(params)
        query["access_key"] = self.api_key
        url = f"{MARKETSTACK_BASE_URL}{endpoint}?{urlencode(query)}"
        data = fetch_json(url, provider="marketstack", timeout_seconds=self.timeout_seconds)
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            message = str(data["error"].get("message") or "MarketStack upstream error.")
            lower = message.lower()
            if "limit" in lower or "usage" in lower:
                raise ProviderError("marketstack", "RATE_LIMIT", message)
            if "access key" in lower or "invalid_api" in lower:
                raise ProviderError("marketstack", "AUTH", message)
            raise ProviderError("marketstack", "UPSTREAM", message)
        return data

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        data = self._request("/eod/latest", {"symbols": symbol, "limit": 1})
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list) or not rows:
            return None
        item = rows[0] if isinstance(rows[0], dict) else None
        if not item:
            return None
        close = _to_float(item.get("close"))
        if close is None or close <= 0:
            return None
        open_value = _to_float(item.get("open")) or close
        high = _to_float(item.get("high")) or close
        low = _to_float(item.get("low")) or close
        previous_close = _to_float(item.get("adj_close")) or close
        timestamp = _to_unix(item.get("date"))
        return NormalizedQuote(
            symbol=symbol,
            price=close,
            change=close - previous_close,
            percent_change=((close - previous_close) / previous_close * 100.0) if previous_close else 0.0,
            high=high,
            low=low,
            open=open_value,
            previous_close=previous_close,
            timestamp=timestamp,
            source="marketstack",
        )

    def get_candles(self, symbol: str, interval: Interval, from_unix: int, to_unix: int) -> list[NormalizedCandle] | None:
        params: dict[str, str | int] = {
            "symbols": symbol,
            "date_from": datetime.fromtimestamp(from_unix, tz=timezone.utc).strftime("%Y-%m-%d"),
            "date_to": datetime.fromtimestamp(to_unix, tz=timezone.utc).strftime("%Y-%m-%d"),
            "limit": 1000,
        }
        if interval in {"1", "5", "15", "30", "60"}:
            params["interval"] = MARKETSTACK_INTERVALS[interval]
        data = self._request("/eod", params)
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return None
        candles: list[NormalizedCandle] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            ts = _to_unix(item.get("date"))
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
        candles.sort(key=lambda c: c.timestamp)
        return candles or None


