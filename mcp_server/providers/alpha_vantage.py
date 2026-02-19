"""Alpha Vantage API client with normalized response models."""

from __future__ import annotations

from datetime import datetime, timezone
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

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
ALPHA_INTERVAL: dict[Interval, str] = {
    "1": "1min",
    "5": "5min",
    "15": "15min",
    "30": "30min",
    "60": "60min",
    "D": "daily",
    "W": "weekly",
    "M": "monthly",
}


def to_number(value: str | int | float | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out


def parse_alpha_error(data: dict) -> ProviderError:
    note = data.get("Note") if isinstance(data.get("Note"), str) else None
    error_message = data.get("Error Message") if isinstance(data.get("Error Message"), str) else None
    information = data.get("Information") if isinstance(data.get("Information"), str) else None
    text = note or error_message or information or "Alpha Vantage returned an error."
    lower = text.lower()
    if note and "frequency" in note.lower():
        return ProviderError("alphavantage", "RATE_LIMIT", text)
    if "api key" in lower:
        return ProviderError("alphavantage", "AUTH", text)
    if "invalid api call" in lower:
        return ProviderError("alphavantage", "UPSTREAM", text)
    if error_message:
        return ProviderError("alphavantage", "NOT_FOUND", text)
    return ProviderError("alphavantage", "UPSTREAM", text)


def parse_timestamp_seconds(value: str) -> int | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%dT%H%M%S"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    return None


def parse_series_entry(timestamp: str, values: dict[str, str]) -> NormalizedCandle | None:
    seconds = parse_timestamp_seconds(timestamp)
    if seconds is None:
        return None
    open_value = to_number(values.get("1. open"))
    high = to_number(values.get("2. high"))
    low = to_number(values.get("3. low"))
    close = to_number(values.get("4. close"))
    volume = to_number(values.get("5. volume")) or to_number(values.get("6. volume")) or 0.0
    if open_value is None or high is None or low is None or close is None:
        return None
    return NormalizedCandle(
        timestamp=seconds,
        open=open_value,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


class AlphaVantageClient:
    """Thin wrapper around Alpha Vantage endpoints used by MCP tools."""

    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _request(self, params: dict[str, str | int | None]) -> dict:
        clean: dict[str, str | int] = {}
        for key, value in params.items():
            if value is not None:
                clean[key] = value
        clean["apikey"] = self.api_key
        url = f"{ALPHA_VANTAGE_BASE_URL}?{urlencode(clean)}"
        data = fetch_json(url, provider="alphavantage", timeout_seconds=self.timeout_seconds)
        if isinstance(data, dict) and (data.get("Note") or data.get("Error Message") or data.get("Information")):
            raise parse_alpha_error(data)
        return data

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        data = self._request({"function": "GLOBAL_QUOTE", "symbol": symbol})
        quote = data.get("Global Quote")
        if not isinstance(quote, dict):
            return None
        price = to_number(quote.get("05. price"))
        if price is None or price <= 0:
            return None
        change_pct_raw = str(quote.get("10. change percent") or "0").replace("%", "")
        return NormalizedQuote(
            symbol=symbol,
            price=price,
            change=to_number(quote.get("09. change")) or 0.0,
            percent_change=to_number(change_pct_raw) or 0.0,
            high=to_number(quote.get("03. high")) or price,
            low=to_number(quote.get("04. low")) or price,
            open=to_number(quote.get("02. open")) or price,
            previous_close=to_number(quote.get("08. previous close")) or price,
            timestamp=None,
            source="alphavantage",
        )

    def get_company_profile(self, symbol: str) -> NormalizedCompanyProfile | None:
        data = self._request({"function": "OVERVIEW", "symbol": symbol})
        if not data.get("Symbol"):
            return None
        return NormalizedCompanyProfile(
            symbol=symbol,
            name=data.get("Name"),
            exchange=data.get("Exchange"),
            currency=data.get("Currency"),
            country=data.get("Country"),
            industry=data.get("Industry"),
            ipo=data.get("LatestQuarter"),
            market_capitalization=to_number(data.get("MarketCapitalization")),
            website=data.get("OfficialSite"),
            source="alphavantage",
        )

    def get_candles(self, symbol: str, interval: Interval, from_unix: int, to_unix: int) -> list[NormalizedCandle] | None:
        alpha_interval = ALPHA_INTERVAL[interval]
        params: dict[str, str | int | None] = {"symbol": symbol, "outputsize": "full"}
        if interval in {"1", "5", "15", "30", "60"}:
            function_name = "TIME_SERIES_INTRADAY"
            series_key = f"Time Series ({alpha_interval})"
            params["interval"] = alpha_interval
        elif interval == "D":
            function_name = "TIME_SERIES_DAILY"
            series_key = "Time Series (Daily)"
        elif interval == "W":
            function_name = "TIME_SERIES_WEEKLY"
            series_key = "Weekly Time Series"
        else:
            function_name = "TIME_SERIES_MONTHLY"
            series_key = "Monthly Time Series"
        params["function"] = function_name
        data = self._request(params)
        series = data.get(series_key)
        if not isinstance(series, dict):
            return None
        candles: list[NormalizedCandle] = []
        for timestamp, values in series.items():
            if not isinstance(values, dict):
                continue
            candle = parse_series_entry(str(timestamp), values)
            if candle and from_unix <= candle.timestamp <= to_unix:
                candles.append(candle)
        candles.sort(key=lambda c: c.timestamp)
        return candles

    def get_news(self, symbol: str, limit: int) -> list[NormalizedNewsItem] | None:
        data = self._request(
            {"function": "NEWS_SENTIMENT", "tickers": symbol, "limit": limit, "sort": "LATEST"}
        )
        feed = data.get("feed")
        if not isinstance(feed, list) or not feed:
            return None
        out: list[NormalizedNewsItem] = []
        for item in feed:
            if not isinstance(item, dict):
                continue
            timestamp = parse_timestamp_seconds(str(item.get("time_published", "")))
            out.append(
                NormalizedNewsItem(
                    headline=str(item.get("title") or "Untitled"),
                    summary=item.get("summary"),
                    url=item.get("url"),
                    source=item.get("source"),
                    datetime=timestamp,
                )
            )
        return out

    def get_rsi(self, symbol: str, interval: Interval, period: int) -> list[NormalizedRsiPoint] | None:
        data = self._request(
            {
                "function": "RSI",
                "symbol": symbol,
                "interval": ALPHA_INTERVAL[interval],
                "time_period": period,
                "series_type": "close",
            }
        )
        rsi_data = data.get("Technical Analysis: RSI")
        if not isinstance(rsi_data, dict):
            return None
        points: list[NormalizedRsiPoint] = []
        for timestamp, values in rsi_data.items():
            if not isinstance(values, dict):
                continue
            seconds = parse_timestamp_seconds(str(timestamp))
            value = to_number(values.get("RSI"))
            if seconds is None or value is None:
                continue
            points.append(NormalizedRsiPoint(timestamp=seconds, value=value))
        points.sort(key=lambda p: p.timestamp)
        return points

    def get_macd(self, symbol: str, interval: Interval) -> list[NormalizedMacdPoint] | None:
        data = self._request(
            {
                "function": "MACD",
                "symbol": symbol,
                "interval": ALPHA_INTERVAL[interval],
                "series_type": "close",
            }
        )
        macd_data = data.get("Technical Analysis: MACD")
        if not isinstance(macd_data, dict):
            return None
        points: list[NormalizedMacdPoint] = []
        for timestamp, values in macd_data.items():
            if not isinstance(values, dict):
                continue
            seconds = parse_timestamp_seconds(str(timestamp))
            macd = to_number(values.get("MACD"))
            signal = to_number(values.get("MACD_Signal"))
            hist = to_number(values.get("MACD_Hist")) or 0.0
            if seconds is None or macd is None or signal is None:
                continue
            points.append(NormalizedMacdPoint(timestamp=seconds, macd=macd, signal=signal, histogram=hist))
        points.sort(key=lambda p: p.timestamp)
        return points

    def get_key_financials(self, symbol: str) -> NormalizedKeyFinancials | None:
        data = self._request({"function": "OVERVIEW", "symbol": symbol})
        if not data.get("Symbol"):
            return None
        return NormalizedKeyFinancials(
            symbol=symbol,
            pe_ratio=to_number(data.get("PERatio")),
            eps=to_number(data.get("EPS")),
            book_value=to_number(data.get("BookValue")),
            dividend_yield=to_number(data.get("DividendYield")),
            week_52_high=to_number(data.get("52WeekHigh")),
            week_52_low=to_number(data.get("52WeekLow")),
            market_capitalization=to_number(data.get("MarketCapitalization")),
            beta=to_number(data.get("Beta")),
            source="alphavantage",
        )


