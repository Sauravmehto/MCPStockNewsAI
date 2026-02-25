"""Finnhub API client with normalized response models."""

from __future__ import annotations

from urllib.parse import urlencode

from mcp_server.providers.http import ProviderError, fetch_json
from mcp_server.providers.models import (
    Interval,
    NormalizedCandle,
    NormalizedCompanyProfile,
    NormalizedKeyFinancials,
    NormalizedMacdPoint,
    NormalizedNewsItem,
    NormalizedQuote,
    NormalizedRsiPoint,
)

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
FINNHUB_RESOLUTION: dict[Interval, str] = {
    "1": "1",
    "5": "5",
    "15": "15",
    "30": "30",
    "60": "60",
    "D": "D",
    "W": "W",
    "M": "M",
}


class FinnhubClient:
    """Thin wrapper around Finnhub REST endpoints used by MCP tools."""

    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _request(self, endpoint: str, query: dict[str, str | int | float | None]) -> dict:
        params: dict[str, str | int | float] = {}
        for key, value in query.items():
            if value is not None:
                params[key] = value
        params["token"] = self.api_key
        url = f"{FINNHUB_BASE_URL}{endpoint}?{urlencode(params)}"
        data = fetch_json(url, provider="finnhub", timeout_seconds=self.timeout_seconds)
        if isinstance(data, dict) and data.get("error"):
            text = str(data["error"])
            lower = text.lower()
            if "limit" in lower:
                raise ProviderError("finnhub", "RATE_LIMIT", text)
            if "token" in lower or "auth" in lower:
                raise ProviderError("finnhub", "AUTH", text)
            raise ProviderError("finnhub", "UPSTREAM", text)
        return data

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        data = self._request("/quote", {"symbol": symbol})
        price = data.get("c")
        if not isinstance(price, (int, float)) or price <= 0:
            return None
        return NormalizedQuote(
            symbol=symbol,
            price=float(price),
            change=float(data.get("d", 0) or 0),
            percent_change=float(data.get("dp", 0) or 0),
            high=float(data.get("h", price) or price),
            low=float(data.get("l", price) or price),
            open=float(data.get("o", price) or price),
            previous_close=float(data.get("pc", price) or price),
            timestamp=int(data["t"]) if isinstance(data.get("t"), (int, float)) else None,
            source="finnhub",
        )

    def get_company_profile(self, symbol: str) -> NormalizedCompanyProfile | None:
        data = self._request("/stock/profile2", {"symbol": symbol})
        if not data.get("ticker"):
            return None
        return NormalizedCompanyProfile(
            symbol=symbol,
            name=data.get("name"),
            exchange=data.get("exchange"),
            currency=data.get("currency"),
            country=data.get("country"),
            industry=data.get("finnhubIndustry"),
            ipo=data.get("ipo"),
            market_capitalization=float(data["marketCapitalization"])
            if isinstance(data.get("marketCapitalization"), (int, float))
            else None,
            website=data.get("weburl"),
            logo=data.get("logo"),
            source="finnhub",
        )

    def get_candles(self, symbol: str, interval: Interval, from_unix: int, to_unix: int) -> list[NormalizedCandle] | None:
        data = self._request(
            "/stock/candle",
            {
                "symbol": symbol,
                "resolution": FINNHUB_RESOLUTION[interval],
                "from": from_unix,
                "to": to_unix,
            },
        )
        timestamps = data.get("t") or []
        if data.get("s") != "ok" or not timestamps:
            return None
        candles: list[NormalizedCandle] = []
        for idx, timestamp in enumerate(timestamps):
            candles.append(
                NormalizedCandle(
                    timestamp=int(timestamp),
                    open=float((data.get("o") or [0])[idx]),
                    high=float((data.get("h") or [0])[idx]),
                    low=float((data.get("l") or [0])[idx]),
                    close=float((data.get("c") or [0])[idx]),
                    volume=float((data.get("v") or [0])[idx]),
                )
            )
        return candles

    def get_news(self, symbol: str, from_date: str, to_date: str, limit: int) -> list[NormalizedNewsItem] | None:
        data = self._request("/company-news", {"symbol": symbol, "from": from_date, "to": to_date})
        if not isinstance(data, list):
            return None
        news = [item for item in data if isinstance(item, dict) and item.get("headline")]
        if not news:
            return None
        out: list[NormalizedNewsItem] = []
        for item in news[:limit]:
            out.append(
                NormalizedNewsItem(
                    headline=str(item.get("headline") or "Untitled"),
                    summary=item.get("summary"),
                    url=item.get("url"),
                    source=item.get("source"),
                    datetime=int(item["datetime"]) if isinstance(item.get("datetime"), (int, float)) else None,
                )
            )
        return out

    def get_rsi(
        self,
        symbol: str,
        interval: Interval,
        from_unix: int,
        to_unix: int,
        period: int,
    ) -> list[NormalizedRsiPoint] | None:
        data = self._request(
            "/indicator",
            {
                "symbol": symbol,
                "resolution": FINNHUB_RESOLUTION[interval],
                "from": from_unix,
                "to": to_unix,
                "indicator": "rsi",
                "timeperiod": period,
            },
        )
        timestamps = data.get("t") or []
        values = data.get("rsi") or []
        if data.get("s") != "ok" or not timestamps or not values:
            return None
        points: list[NormalizedRsiPoint] = []
        for idx, timestamp in enumerate(timestamps):
            value = values[idx] if idx < len(values) else None
            if isinstance(value, (int, float)):
                points.append(NormalizedRsiPoint(timestamp=int(timestamp), value=float(value)))
        return points

    def get_macd(
        self,
        symbol: str,
        interval: Interval,
        from_unix: int,
        to_unix: int,
        fast_period: int,
        slow_period: int,
        signal_period: int,
    ) -> list[NormalizedMacdPoint] | None:
        data = self._request(
            "/indicator",
            {
                "symbol": symbol,
                "resolution": FINNHUB_RESOLUTION[interval],
                "from": from_unix,
                "to": to_unix,
                "indicator": "macd",
                "fastperiod": fast_period,
                "slowperiod": slow_period,
                "signalperiod": signal_period,
            },
        )
        timestamps = data.get("t") or []
        macd_vals = data.get("macd") or []
        signal_vals = data.get("signal") or []
        hist_vals = data.get("histogram") or []
        if data.get("s") != "ok" or not timestamps or not macd_vals or not signal_vals:
            return None
        points: list[NormalizedMacdPoint] = []
        for idx, timestamp in enumerate(timestamps):
            macd = macd_vals[idx] if idx < len(macd_vals) else None
            signal = signal_vals[idx] if idx < len(signal_vals) else None
            hist = hist_vals[idx] if idx < len(hist_vals) and isinstance(hist_vals[idx], (int, float)) else 0.0
            if isinstance(macd, (int, float)) and isinstance(signal, (int, float)):
                points.append(
                    NormalizedMacdPoint(
                        timestamp=int(timestamp),
                        macd=float(macd),
                        signal=float(signal),
                        histogram=float(hist),
                    )
                )
        return points

    def get_key_financials(self, symbol: str) -> NormalizedKeyFinancials | None:
        data = self._request("/stock/metric", {"symbol": symbol, "metric": "all"})
        metrics = data.get("metric")
        if not isinstance(metrics, dict):
            return None

        def _num(key: str) -> float | None:
            value = metrics.get(key)
            return float(value) if isinstance(value, (int, float)) else None

        return NormalizedKeyFinancials(
            symbol=symbol,
            pe_ratio=_num("peBasicExclExtraTTM"),
            eps=_num("epsBasicExclExtraItemsTTM"),
            book_value=_num("bookValuePerShareQuarterly"),
            dividend_yield=_num("dividendYieldIndicatedAnnual"),
            week_52_high=_num("52WeekHigh"),
            week_52_low=_num("52WeekLow"),
            market_capitalization=_num("marketCapitalization"),
            beta=_num("beta"),
            source="finnhub",
        )


