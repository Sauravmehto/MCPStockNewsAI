"""Stock-domain orchestration service."""

from __future__ import annotations

import time

from mcp_server.providers.alpha_vantage import AlphaVantageClient
from mcp_server.providers.finnhub import FinnhubClient
from mcp_server.providers.fmp import FmpClient
from mcp_server.providers.marketstack import MarketStackClient
from mcp_server.providers.models import (
    NormalizedCandle,
    NormalizedCompanyProfile,
    NormalizedDividendEvent,
    NormalizedEarningsEvent,
    NormalizedNewsItem,
    NormalizedQuote,
    NormalizedSplitEvent,
)
from mcp_server.providers.twelve_data import TwelveDataClient
from mcp_server.providers.web_quote_search import WebQuoteSearchClient
from mcp_server.providers.yahoo_finance import YahooFinanceClient
from mcp_server.services.base import ServiceContext, ServiceResult, run_with_cache, validate_suspicious_quote_movement
from mcp_server.services.fallback_manager import FallbackManager, ProviderAttempt
from mcp_server.services.provider_status import ProviderStatus


class StockService:
    def __init__(self, ctx: ServiceContext) -> None:
        self.ctx = ctx
        status = self.ctx.get_provider("provider_status")
        if not isinstance(status, ProviderStatus):
            status = ProviderStatus()
            self.ctx.providers["provider_status"] = status
        self.fallback_manager = FallbackManager(ctx=self.ctx, provider_status=status)

    def _finnhub(self) -> FinnhubClient | None:
        client = self.ctx.get_provider("finnhub")
        return client if isinstance(client, FinnhubClient) else None

    def _alpha(self) -> AlphaVantageClient | None:
        client = self.ctx.get_provider("alphavantage")
        return client if isinstance(client, AlphaVantageClient) else None

    def _fmp(self) -> FmpClient | None:
        client = self.ctx.get_provider("fmp")
        return client if isinstance(client, FmpClient) else None

    def _twelve_data(self) -> TwelveDataClient | None:
        client = self.ctx.get_provider("twelvedata")
        return client if isinstance(client, TwelveDataClient) else None

    def _marketstack(self) -> MarketStackClient | None:
        client = self.ctx.get_provider("marketstack")
        return client if isinstance(client, MarketStackClient) else None

    def _web_search(self) -> WebQuoteSearchClient | None:
        client = self.ctx.get_provider("websearch")
        return client if isinstance(client, WebQuoteSearchClient) else None

    def _yahoo(self) -> YahooFinanceClient | None:
        client = self.ctx.get_provider("yahoo")
        return client if isinstance(client, YahooFinanceClient) else None

    def get_quote(self, symbol: str) -> ServiceResult[NormalizedQuote]:
        result = run_with_cache(
            self.ctx,
            f"stock:quote:{symbol}",
            lambda: self.fallback_manager.execute(
                operation="get_quote",
                symbol=symbol,
                attempts=[
                    ProviderAttempt("alphavantage", "Alpha Vantage", lambda: self._alpha().get_quote(symbol) if self._alpha() else None),
                    ProviderAttempt("finnhub", "Finnhub", lambda: self._finnhub().get_quote(symbol) if self._finnhub() else None),
                    ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_quote(symbol) if self._fmp() else None),
                    ProviderAttempt("twelvedata", "TwelveData", lambda: self._twelve_data().get_quote(symbol) if self._twelve_data() else None),
                    ProviderAttempt("marketstack", "MarketStack", lambda: self._marketstack().get_quote(symbol) if self._marketstack() else None),
                    ProviderAttempt("websearch", "Web Search", lambda: self._web_search().get_quote(symbol) if self._web_search() else None),
                ],
            ),
            ttl_seconds=15,
        )
        if result.data:
            suspicious = validate_suspicious_quote_movement(result.data.price, result.data.previous_close)
            if suspicious:
                result.warning = f"{result.warning} {suspicious}".strip() if result.warning else suspicious
        return result

    def get_profile(self, symbol: str) -> ServiceResult[NormalizedCompanyProfile]:
        return run_with_cache(
            self.ctx,
            f"stock:profile:{symbol}",
            lambda: self.fallback_manager.execute(
                operation="get_company_profile",
                symbol=symbol,
                attempts=[
                    ProviderAttempt("alphavantage", "Alpha Vantage", lambda: self._alpha().get_company_profile(symbol) if self._alpha() else None),
                    ProviderAttempt("finnhub", "Finnhub", lambda: self._finnhub().get_company_profile(symbol) if self._finnhub() else None),
                    ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_company_profile(symbol) if self._fmp() else None),
                    ProviderAttempt("twelvedata", "TwelveData", lambda: self._twelve_data().get_company_profile(symbol) if self._twelve_data() else None),
                ],
            ),
            ttl_seconds=3600,
        )

    def get_history(self, symbol: str, interval: str, from_unix: int, to_unix: int) -> ServiceResult[list[NormalizedCandle]]:
        return run_with_cache(
            self.ctx,
            f"stock:candles:{symbol}:{interval}:{from_unix}:{to_unix}",
            lambda: self.fallback_manager.execute(
                operation="get_candles",
                symbol=symbol,
                attempts=[
                    ProviderAttempt("alphavantage", "Alpha Vantage", lambda: self._alpha().get_candles(symbol, interval, from_unix, to_unix) if self._alpha() else None),
                    ProviderAttempt("finnhub", "Finnhub", lambda: self._finnhub().get_candles(symbol, interval, from_unix, to_unix) if self._finnhub() else None),
                    ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_candles(symbol, interval, from_unix, to_unix) if self._fmp() else None),
                    ProviderAttempt("twelvedata", "TwelveData", lambda: self._twelve_data().get_candles(symbol, interval, from_unix, to_unix) if self._twelve_data() else None),
                    ProviderAttempt("marketstack", "MarketStack", lambda: self._marketstack().get_candles(symbol, interval, from_unix, to_unix) if self._marketstack() else None),
                ],
            ),
            ttl_seconds=60,
        )

    def get_news(self, symbol: str, from_date: str, to_date: str, limit: int = 10) -> ServiceResult[list[NormalizedNewsItem]]:
        return run_with_cache(
            self.ctx,
            f"stock:news:{symbol}:{from_date}:{to_date}:{limit}",
            lambda: self.fallback_manager.execute(
                operation="get_stock_news",
                symbol=symbol,
                attempts=[
                    ProviderAttempt("alphavantage", "Alpha Vantage", lambda: self._alpha().get_news(symbol, limit) if self._alpha() else None),
                    ProviderAttempt("finnhub", "Finnhub", lambda: self._finnhub().get_news(symbol, from_date, to_date, limit) if self._finnhub() else None),
                    ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_news(symbol, limit) if self._fmp() else None),
                    ProviderAttempt("twelvedata", "TwelveData", lambda: self._twelve_data().get_news(symbol, limit) if self._twelve_data() else None),
                ],
            ),
            ttl_seconds=300,
        )

    def get_premarket_data(self, symbol: str) -> ServiceResult[dict[str, float | int | str]]:
        return run_with_cache(
            self.ctx,
            f"stock:premarket:{symbol}",
            lambda: self.fallback_manager.execute(
                operation="get_premarket_data",
                symbol=symbol,
                attempts=[
                    ProviderAttempt("yahoo", "Yahoo Finance", lambda: self._yahoo_premarket(symbol)),
                    ProviderAttempt("websearch", "Web Search", lambda: self._web_premarket(symbol)),
                ],
            ),
            ttl_seconds=15,
        )

    def _yahoo_premarket(self, symbol: str) -> dict[str, float | int | str] | None:
        yahoo = self._yahoo()
        if not yahoo:
            return None
        quote = yahoo.get_quote(symbol)
        if not quote:
            return None
        return {"symbol": symbol, "price": quote.price, "volume": 0, "change_pct": quote.percent_change, "session": "extended"}

    def _web_premarket(self, symbol: str) -> dict[str, float | int | str] | None:
        web = self._web_search()
        quote = web.get_quote(symbol) if web else None
        if not quote:
            return None
        return {"symbol": symbol, "price": quote.price, "volume": 0, "change_pct": quote.percent_change, "session": "extended"}

    def search_symbol(self, query: str, limit: int = 10) -> ServiceResult[list[dict[str, str]]]:
        query_text = query.strip()
        return run_with_cache(
            self.ctx,
            f"stock:search:{query_text}:{limit}",
            lambda: self.fallback_manager.execute(
                operation="search_symbol",
                symbol=query_text,
                attempts=[
                    ProviderAttempt(
                        "websearch",
                        "Web Search",
                        lambda: [{"symbol": query_text.upper(), "name": f"{query_text} (best match)"}] if query_text else None,
                    )
                ],
            ),
            ttl_seconds=300,
        )

    def get_watchlist_summary(self, symbols: list[str]) -> ServiceResult[list[dict[str, float | str]]]:
        rows: list[dict[str, float | str]] = []
        source: str | None = None
        warning: str | None = None
        for symbol in symbols[:25]:
            quote_result = self.get_quote(symbol)
            if not quote_result.data:
                continue
            source = source or quote_result.source
            warning = warning or quote_result.warning
            sentiment = "neutral"
            if quote_result.data.percent_change > 1:
                sentiment = "bullish"
            elif quote_result.data.percent_change < -1:
                sentiment = "bearish"
            rows.append({"symbol": symbol, "price": quote_result.data.price, "change_pct": quote_result.data.percent_change, "sentiment": sentiment})
        return ServiceResult(data=rows, source=source, warning=warning, fetched_at=time.time(), data_provider=source, data_license="Provider terms apply")

    def get_dividends(self, symbol: str, limit: int = 12) -> ServiceResult[list[NormalizedDividendEvent]]:
        return run_with_cache(
            self.ctx,
            f"stock:dividends:{symbol}:{limit}",
            lambda: self.fallback_manager.execute(
                operation="get_dividends",
                symbol=symbol,
                attempts=[ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_dividends(symbol, limit) if self._fmp() else None)],
            ),
            ttl_seconds=3600,
        )

    def get_splits(self, symbol: str, limit: int = 10) -> ServiceResult[list[NormalizedSplitEvent]]:
        return run_with_cache(
            self.ctx,
            f"stock:splits:{symbol}:{limit}",
            lambda: self.fallback_manager.execute(
                operation="get_splits",
                symbol=symbol,
                attempts=[ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_splits(symbol, limit) if self._fmp() else None)],
            ),
            ttl_seconds=3600,
        )

    def get_earnings_calendar(self, symbol: str, limit: int = 8) -> ServiceResult[list[NormalizedEarningsEvent]]:
        return run_with_cache(
            self.ctx,
            f"stock:earnings:{symbol}:{limit}",
            lambda: self.fallback_manager.execute(
                operation="get_earnings_calendar",
                symbol=symbol,
                attempts=[ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_earnings_calendar(symbol, limit) if self._fmp() else None)],
            ),
            ttl_seconds=3600,
        )
