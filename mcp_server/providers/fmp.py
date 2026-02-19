"""Financial Modeling Prep adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

from mcp_server.providers.http import fetch_json
from mcp_server.providers.models import (
    Interval,
    NormalizedCandle,
    NormalizedCompanyProfile,
    NormalizedDividendEvent,
    NormalizedEarningsEvent,
    NormalizedKeyFinancials,
    NormalizedNewsItem,
    NormalizedQuote,
    NormalizedSplitEvent,
    NormalizedStatement,
)


class FmpClient:
    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.base = "https://financialmodelingprep.com/api/v3"

    def _get(self, path: str) -> object:
        sep = "&" if "?" in path else "?"
        url = f"{self.base}{path}{sep}apikey={self.api_key}"
        return fetch_json(
            url,
            provider="fmp",
            timeout_seconds=self.timeout_seconds,
            headers={"apikey": self.api_key},
        )

    @staticmethod
    def _as_float(value: object) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_unix(value: object) -> int | None:
        if not isinstance(value, str) or not value:
            return None
        if value.endswith("Z"):
            try:
                return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
            except ValueError:
                return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return int(datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).timestamp())
            except ValueError:
                continue
        return None

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        encoded = quote_plus(symbol)
        data = self._get(f"/quote/{encoded}")
        if not isinstance(data, list) or not data:
            return None
        item = data[0] if isinstance(data[0], dict) else None
        if not item:
            return None
        price = self._as_float(item.get("price"))
        if price is None or price <= 0:
            return None
        change = self._as_float(item.get("change")) or 0.0
        percent_change = self._as_float(item.get("changesPercentage")) or 0.0
        high = self._as_float(item.get("dayHigh")) or price
        low = self._as_float(item.get("dayLow")) or price
        open_value = self._as_float(item.get("open")) or price
        previous_close = self._as_float(item.get("previousClose")) or price
        timestamp = int(item["timestamp"]) if isinstance(item.get("timestamp"), (int, float)) else None
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
            source="fmp",
        )

    def get_company_profile(self, symbol: str) -> NormalizedCompanyProfile | None:
        encoded = quote_plus(symbol)
        data = self._get(f"/profile/{encoded}")
        if not isinstance(data, list) or not data:
            return None
        item = data[0] if isinstance(data[0], dict) else None
        if not item:
            return None
        return NormalizedCompanyProfile(
            symbol=symbol,
            name=item.get("companyName") if isinstance(item.get("companyName"), str) else None,
            exchange=item.get("exchangeShortName") if isinstance(item.get("exchangeShortName"), str) else None,
            currency=item.get("currency") if isinstance(item.get("currency"), str) else None,
            country=item.get("country") if isinstance(item.get("country"), str) else None,
            industry=item.get("industry") if isinstance(item.get("industry"), str) else None,
            ipo=item.get("ipoDate") if isinstance(item.get("ipoDate"), str) else None,
            market_capitalization=self._as_float(item.get("mktCap")),
            website=item.get("website") if isinstance(item.get("website"), str) else None,
            logo=item.get("image") if isinstance(item.get("image"), str) else None,
            source="fmp",
        )

    def get_candles(self, symbol: str, interval: Interval, from_unix: int, to_unix: int) -> list[NormalizedCandle] | None:
        if interval in {"W", "M"}:
            # FMP chart endpoint is day/intraday oriented for this implementation.
            return None
        encoded = quote_plus(symbol)
        if interval in {"D"}:
            date_from = datetime.fromtimestamp(from_unix, tz=timezone.utc).strftime("%Y-%m-%d")
            date_to = datetime.fromtimestamp(to_unix, tz=timezone.utc).strftime("%Y-%m-%d")
            path = f"/historical-price-full/{encoded}?from={date_from}&to={date_to}"
            data = self._get(path)
            rows = data.get("historical") if isinstance(data, dict) else None
            if not isinstance(rows, list):
                return None
            candles: list[NormalizedCandle] = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                ts = self._as_unix(item.get("date"))
                open_value = self._as_float(item.get("open"))
                high = self._as_float(item.get("high"))
                low = self._as_float(item.get("low"))
                close = self._as_float(item.get("close"))
                volume = self._as_float(item.get("volume")) or 0.0
                if ts is None or open_value is None or high is None or low is None or close is None:
                    continue
                candles.append(
                    NormalizedCandle(timestamp=ts, open=open_value, high=high, low=low, close=close, volume=volume)
                )
            candles.sort(key=lambda c: c.timestamp)
            return candles or None

        interval_map = {"1": "1min", "5": "5min", "15": "15min", "30": "30min", "60": "1hour"}
        path = f"/historical-chart/{interval_map[interval]}/{encoded}"
        data = self._get(path)
        if not isinstance(data, list):
            return None
        candles = []
        for item in data:
            if not isinstance(item, dict):
                continue
            ts = self._as_unix(item.get("date"))
            if ts is None or ts < from_unix or ts > to_unix:
                continue
            open_value = self._as_float(item.get("open"))
            high = self._as_float(item.get("high"))
            low = self._as_float(item.get("low"))
            close = self._as_float(item.get("close"))
            volume = self._as_float(item.get("volume")) or 0.0
            if open_value is None or high is None or low is None or close is None:
                continue
            candles.append(NormalizedCandle(timestamp=ts, open=open_value, high=high, low=low, close=close, volume=volume))
        candles.sort(key=lambda c: c.timestamp)
        return candles or None

    def get_news(self, symbol: str, limit: int = 10) -> list[NormalizedNewsItem] | None:
        encoded = quote_plus(symbol)
        data = self._get(f"/stock_news?tickers={encoded}&limit={max(1, limit)}")
        if not isinstance(data, list):
            return None
        out: list[NormalizedNewsItem] = []
        for item in data[:limit]:
            if not isinstance(item, dict):
                continue
            out.append(
                NormalizedNewsItem(
                    headline=str(item.get("title") or "Untitled"),
                    summary=item.get("text") if isinstance(item.get("text"), str) else None,
                    url=item.get("url") if isinstance(item.get("url"), str) else None,
                    source=item.get("site") if isinstance(item.get("site"), str) else "FMP",
                    datetime=self._as_unix(item.get("publishedDate")),
                )
            )
        return out or None

    def get_key_metrics(self, symbol: str) -> NormalizedKeyFinancials | None:
        encoded = quote_plus(symbol)
        data = self._get(f"/key-metrics-ttm/{encoded}")
        if not isinstance(data, list) or not data:
            return None
        item = data[0] if isinstance(data[0], dict) else {}
        return NormalizedKeyFinancials(
            symbol=symbol,
            pe_ratio=float(item["peRatioTTM"]) if isinstance(item.get("peRatioTTM"), (int, float)) else None,
            eps=float(item["netIncomePerShareTTM"])
            if isinstance(item.get("netIncomePerShareTTM"), (int, float))
            else None,
            book_value=float(item["bookValuePerShareTTM"])
            if isinstance(item.get("bookValuePerShareTTM"), (int, float))
            else None,
            dividend_yield=float(item["dividendYieldTTM"])
            if isinstance(item.get("dividendYieldTTM"), (int, float))
            else None,
            beta=float(item["beta"]) if isinstance(item.get("beta"), (int, float)) else None,
            source="fmp",
        )

    def get_dividends(self, symbol: str, limit: int = 12) -> list[NormalizedDividendEvent] | None:
        encoded = quote_plus(symbol)
        data = self._get(f"/historical-price-full/stock_dividend/{encoded}?serietype=line")
        historical = (data or {}).get("historical") if isinstance(data, dict) else None
        if not isinstance(historical, list):
            return None
        out: list[NormalizedDividendEvent] = []
        for item in historical[:limit]:
            if not isinstance(item, dict):
                continue
            out.append(
                NormalizedDividendEvent(
                    symbol=symbol,
                    ex_date=item.get("date"),
                    amount=float(item["dividend"]) if isinstance(item.get("dividend"), (int, float)) else None,
                    source="fmp",
                )
            )
        return out or None

    def get_splits(self, symbol: str, limit: int = 10) -> list[NormalizedSplitEvent] | None:
        encoded = quote_plus(symbol)
        data = self._get(f"/historical-price-full/stock_split/{encoded}?serietype=line")
        historical = (data or {}).get("historical") if isinstance(data, dict) else None
        if not isinstance(historical, list):
            return None
        out: list[NormalizedSplitEvent] = []
        for item in historical[:limit]:
            if not isinstance(item, dict):
                continue
            out.append(
                NormalizedSplitEvent(
                    symbol=symbol,
                    date=item.get("date"),
                    ratio=str(item.get("label") or item.get("numerator") or ""),
                    source="fmp",
                )
            )
        return out or None

    def get_earnings_calendar(self, symbol: str, limit: int = 8) -> list[NormalizedEarningsEvent] | None:
        encoded = quote_plus(symbol)
        data = self._get(f"/historical/earning_calendar/{encoded}")
        if not isinstance(data, list):
            return None
        out: list[NormalizedEarningsEvent] = []
        for item in data[:limit]:
            if not isinstance(item, dict):
                continue
            out.append(
                NormalizedEarningsEvent(
                    symbol=symbol,
                    date=item.get("date"),
                    eps_estimate=float(item["epsEstimated"]) if isinstance(item.get("epsEstimated"), (int, float)) else None,
                    eps_actual=float(item["eps"]) if isinstance(item.get("eps"), (int, float)) else None,
                    revenue_estimate=float(item["revenueEstimated"])
                    if isinstance(item.get("revenueEstimated"), (int, float))
                    else None,
                    revenue_actual=float(item["revenue"]) if isinstance(item.get("revenue"), (int, float)) else None,
                    source="fmp",
                )
            )
        return out or None

    def get_statement(
        self, symbol: str, statement_type: str, period: str = "annual"
    ) -> list[NormalizedStatement] | None:
        encoded = quote_plus(symbol)
        path_by_type = {
            "income": "/income-statement",
            "balance": "/balance-sheet-statement",
            "cashflow": "/cash-flow-statement",
        }
        if statement_type not in path_by_type:
            return None
        data = self._get(f"{path_by_type[statement_type]}/{encoded}?period={period}&limit=4")
        if not isinstance(data, list):
            return None
        out: list[NormalizedStatement] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            out.append(
                NormalizedStatement(
                    symbol=symbol,
                    statement_type=statement_type,  # type: ignore[arg-type]
                    period=item.get("date"),
                    values=item,
                    source="fmp",
                )
            )
        return out or None


