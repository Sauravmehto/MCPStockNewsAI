"""Yahoo Finance adapter with normalized outputs."""

from __future__ import annotations

from urllib.parse import quote_plus

from mcp_server.providers.http import fetch_json
from mcp_server.providers.models import (
    Interval,
    NormalizedCandle,
    NormalizedCompanyProfile,
    NormalizedNewsItem,
    NormalizedOptionsContract,
    NormalizedQuote,
)

YAHOO_CHART_INTERVAL: dict[Interval, str] = {
    "1": "1m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "60m",
    "D": "1d",
    "W": "1wk",
    "M": "1mo",
}


class YahooFinanceClient:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        encoded = quote_plus(symbol)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={encoded}"
        data = fetch_json(url, provider="yahoo", timeout_seconds=self.timeout_seconds)
        items = ((data or {}).get("quoteResponse") or {}).get("result") or []
        if not items:
            return None
        item = items[0]
        price = item.get("regularMarketPrice")
        if not isinstance(price, (int, float)):
            return None
        change = item.get("regularMarketChange")
        change_pct = item.get("regularMarketChangePercent")
        return NormalizedQuote(
            symbol=symbol,
            price=float(price),
            change=float(change or 0.0),
            percent_change=float(change_pct or 0.0),
            high=float(item.get("regularMarketDayHigh") or price),
            low=float(item.get("regularMarketDayLow") or price),
            open=float(item.get("regularMarketOpen") or price),
            previous_close=float(item.get("regularMarketPreviousClose") or price),
            timestamp=int(item["regularMarketTime"]) if isinstance(item.get("regularMarketTime"), int) else None,
            source="yahoo",
        )

    def get_profile(self, symbol: str) -> NormalizedCompanyProfile | None:
        encoded = quote_plus(symbol)
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{encoded}?modules=assetProfile"
        data = fetch_json(url, provider="yahoo", timeout_seconds=self.timeout_seconds)
        results = ((data or {}).get("quoteSummary") or {}).get("result") or []
        if not results:
            return None
        profile = (results[0] or {}).get("assetProfile") or {}
        if not profile:
            return None
        return NormalizedCompanyProfile(
            symbol=symbol,
            name=profile.get("longBusinessSummary"),
            exchange=None,
            currency=None,
            country=profile.get("country"),
            industry=profile.get("industry"),
            website=profile.get("website"),
            source="yahoo",
        )

    def get_candles(
        self,
        symbol: str,
        interval: Interval,
        from_unix: int,
        to_unix: int,
    ) -> list[NormalizedCandle] | None:
        encoded = quote_plus(symbol)
        chart_interval = YAHOO_CHART_INTERVAL[interval]
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{encoded}?period1={from_unix}&period2={to_unix}&interval={chart_interval}"
        )
        data = fetch_json(url, provider="yahoo", timeout_seconds=self.timeout_seconds)
        result = ((data or {}).get("chart") or {}).get("result") or []
        if not result:
            return None
        item = result[0]
        timestamps = item.get("timestamp") or []
        quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        candles: list[NormalizedCandle] = []
        for idx, ts in enumerate(timestamps):
            o = opens[idx] if idx < len(opens) else None
            h = highs[idx] if idx < len(highs) else None
            l = lows[idx] if idx < len(lows) else None
            c = closes[idx] if idx < len(closes) else None
            v = volumes[idx] if idx < len(volumes) else None
            if not all(isinstance(x, (int, float)) for x in [o, h, l, c]):
                continue
            candles.append(
                NormalizedCandle(
                    timestamp=int(ts),
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v or 0.0),
                )
            )
        return candles or None

    def get_news(self, symbol: str, limit: int = 10) -> list[NormalizedNewsItem] | None:
        encoded = quote_plus(symbol)
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={encoded}&newsCount={max(1, limit)}"
        data = fetch_json(url, provider="yahoo", timeout_seconds=self.timeout_seconds)
        items = (data or {}).get("news") or []
        if not items:
            return None
        out: list[NormalizedNewsItem] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            out.append(
                NormalizedNewsItem(
                    headline=str(item.get("title") or "Untitled"),
                    summary=item.get("summary"),
                    url=item.get("link"),
                    source=(item.get("publisher") or "Yahoo Finance"),
                    datetime=int(item["providerPublishTime"]) if isinstance(item.get("providerPublishTime"), int) else None,
                )
            )
        return out or None

    def get_options_chain(self, symbol: str) -> list[NormalizedOptionsContract] | None:
        encoded = quote_plus(symbol)
        url = f"https://query2.finance.yahoo.com/v7/finance/options/{encoded}"
        data = fetch_json(url, provider="yahoo", timeout_seconds=self.timeout_seconds)
        result = ((data or {}).get("optionChain") or {}).get("result") or []
        if not result:
            return None
        options = (result[0] or {}).get("options") or []
        if not options:
            return None
        contracts = options[0]
        expiry = str(contracts.get("expirationDate") or "")
        out: list[NormalizedOptionsContract] = []
        for contract in (contracts.get("calls") or []):
            strike = contract.get("strike")
            if not isinstance(strike, (int, float)):
                continue
            out.append(
                NormalizedOptionsContract(
                    symbol=symbol,
                    expiration=expiry,
                    strike=float(strike),
                    call_put="call",
                    bid=float(contract["bid"]) if isinstance(contract.get("bid"), (int, float)) else None,
                    ask=float(contract["ask"]) if isinstance(contract.get("ask"), (int, float)) else None,
                    last=float(contract["lastPrice"]) if isinstance(contract.get("lastPrice"), (int, float)) else None,
                    volume=int(contract["volume"]) if isinstance(contract.get("volume"), (int, float)) else None,
                    open_interest=int(contract["openInterest"])
                    if isinstance(contract.get("openInterest"), (int, float))
                    else None,
                    implied_volatility=float(contract["impliedVolatility"])
                    if isinstance(contract.get("impliedVolatility"), (int, float))
                    else None,
                    delta=float(contract["delta"]) if isinstance(contract.get("delta"), (int, float)) else None,
                    gamma=float(contract["gamma"]) if isinstance(contract.get("gamma"), (int, float)) else None,
                    theta=float(contract["theta"]) if isinstance(contract.get("theta"), (int, float)) else None,
                    vega=float(contract["vega"]) if isinstance(contract.get("vega"), (int, float)) else None,
                    source="yahoo",
                )
            )
        for contract in (contracts.get("puts") or []):
            strike = contract.get("strike")
            if not isinstance(strike, (int, float)):
                continue
            out.append(
                NormalizedOptionsContract(
                    symbol=symbol,
                    expiration=expiry,
                    strike=float(strike),
                    call_put="put",
                    bid=float(contract["bid"]) if isinstance(contract.get("bid"), (int, float)) else None,
                    ask=float(contract["ask"]) if isinstance(contract.get("ask"), (int, float)) else None,
                    last=float(contract["lastPrice"]) if isinstance(contract.get("lastPrice"), (int, float)) else None,
                    volume=int(contract["volume"]) if isinstance(contract.get("volume"), (int, float)) else None,
                    open_interest=int(contract["openInterest"])
                    if isinstance(contract.get("openInterest"), (int, float))
                    else None,
                    implied_volatility=float(contract["impliedVolatility"])
                    if isinstance(contract.get("impliedVolatility"), (int, float))
                    else None,
                    delta=float(contract["delta"]) if isinstance(contract.get("delta"), (int, float)) else None,
                    gamma=float(contract["gamma"]) if isinstance(contract.get("gamma"), (int, float)) else None,
                    theta=float(contract["theta"]) if isinstance(contract.get("theta"), (int, float)) else None,
                    vega=float(contract["vega"]) if isinstance(contract.get("vega"), (int, float)) else None,
                    source="yahoo",
                )
            )
        return out or None


