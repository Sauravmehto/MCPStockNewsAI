"""Stock-domain orchestration service."""

from __future__ import annotations

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
from mcp_server.services.base import ServiceContext, ServiceResult, run_with_cache
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

    def get_quote(self, symbol: str) -> ServiceResult[NormalizedQuote]:
        cache_key = f"stock:quote:{symbol}"
        return run_with_cache(
            self.ctx,
            cache_key,
            lambda: self.fallback_manager.execute(
                operation="get_quote",
                symbol=symbol,
                attempts=[
                    ProviderAttempt("alphavantage", "Alpha Vantage", lambda: self._alpha().get_quote(symbol) if self._alpha() else None),
                    ProviderAttempt("finnhub", "Finnhub", lambda: self._finnhub().get_quote(symbol) if self._finnhub() else None),
                    ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_quote(symbol) if self._fmp() else None),
                    ProviderAttempt(
                        "twelvedata",
                        "TwelveData",
                        lambda: self._twelve_data().get_quote(symbol) if self._twelve_data() else None,
                    ),
                    ProviderAttempt(
                        "marketstack",
                        "MarketStack",
                        lambda: self._marketstack().get_quote(symbol) if self._marketstack() else None,
                    ),
                    ProviderAttempt(
                        "websearch",
                        "Web Search",
                        lambda: self._web_search().get_quote(symbol) if self._web_search() else None,
                    ),
                ],
            ),
        )

    def get_profile(self, symbol: str) -> ServiceResult[NormalizedCompanyProfile]:
        cache_key = f"stock:profile:{symbol}"
        return run_with_cache(
            self.ctx,
            cache_key,
            lambda: self.fallback_manager.execute(
                operation="get_company_profile",
                symbol=symbol,
                attempts=[
                    ProviderAttempt(
                        "alphavantage",
                        "Alpha Vantage",
                        lambda: self._alpha().get_company_profile(symbol) if self._alpha() else None,
                    ),
                    ProviderAttempt(
                        "finnhub",
                        "Finnhub",
                        lambda: self._finnhub().get_company_profile(symbol) if self._finnhub() else None,
                    ),
                    ProviderAttempt(
                        "fmp",
                        "FMP",
                        lambda: self._fmp().get_company_profile(symbol) if self._fmp() else None,
                    ),
                    ProviderAttempt(
                        "twelvedata",
                        "TwelveData",
                        lambda: self._twelve_data().get_company_profile(symbol) if self._twelve_data() else None,
                    ),
                ],
            ),
        )

    def get_history(
        self,
        symbol: str,
        interval: str,
        from_unix: int,
        to_unix: int,
    ) -> ServiceResult[list[NormalizedCandle]]:
        cache_key = f"stock:candles:{symbol}:{interval}:{from_unix}:{to_unix}"
        return run_with_cache(
            self.ctx,
            cache_key,
            lambda: self.fallback_manager.execute(
                operation="get_candles",
                symbol=symbol,
                attempts=[
                    ProviderAttempt(
                        "alphavantage",
                        "Alpha Vantage",
                        lambda: self._alpha().get_candles(symbol, interval, from_unix, to_unix) if self._alpha() else None,
                    ),
                    ProviderAttempt(
                        "finnhub",
                        "Finnhub",
                        lambda: self._finnhub().get_candles(symbol, interval, from_unix, to_unix) if self._finnhub() else None,
                    ),
                    ProviderAttempt(
                        "fmp",
                        "FMP",
                        lambda: self._fmp().get_candles(symbol, interval, from_unix, to_unix) if self._fmp() else None,
                    ),
                    ProviderAttempt(
                        "twelvedata",
                        "TwelveData",
                        lambda: self._twelve_data().get_candles(symbol, interval, from_unix, to_unix)
                        if self._twelve_data()
                        else None,
                    ),
                    ProviderAttempt(
                        "marketstack",
                        "MarketStack",
                        lambda: self._marketstack().get_candles(symbol, interval, from_unix, to_unix)
                        if self._marketstack()
                        else None,
                    ),
                ],
            ),
        )

    def get_news(self, symbol: str, from_date: str, to_date: str, limit: int = 10) -> ServiceResult[list[NormalizedNewsItem]]:
        cache_key = f"stock:news:{symbol}:{from_date}:{to_date}:{limit}"
        return run_with_cache(
            self.ctx,
            cache_key,
            lambda: self.fallback_manager.execute(
                operation="get_stock_news",
                symbol=symbol,
                attempts=[
                    ProviderAttempt("alphavantage", "Alpha Vantage", lambda: self._alpha().get_news(symbol, limit) if self._alpha() else None),
                    ProviderAttempt(
                        "finnhub",
                        "Finnhub",
                        lambda: self._finnhub().get_news(symbol, from_date, to_date, limit) if self._finnhub() else None,
                    ),
                    ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_news(symbol, limit) if self._fmp() else None),
                    ProviderAttempt(
                        "twelvedata",
                        "TwelveData",
                        lambda: self._twelve_data().get_news(symbol, limit) if self._twelve_data() else None,
                    ),
                ],
            ),
        )

    def get_dividends(self, symbol: str, limit: int = 12) -> ServiceResult[list[NormalizedDividendEvent]]:
        return self.fallback_manager.execute(
            operation="get_dividends",
            symbol=symbol,
            attempts=[
                ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_dividends(symbol, limit) if self._fmp() else None),
            ],
        )

    def get_splits(self, symbol: str, limit: int = 10) -> ServiceResult[list[NormalizedSplitEvent]]:
        return self.fallback_manager.execute(
            operation="get_splits",
            symbol=symbol,
            attempts=[
                ProviderAttempt("fmp", "FMP", lambda: self._fmp().get_splits(symbol, limit) if self._fmp() else None),
            ],
        )

    def get_earnings_calendar(self, symbol: str, limit: int = 8) -> ServiceResult[list[NormalizedEarningsEvent]]:
        return self.fallback_manager.execute(
            operation="get_earnings_calendar",
            symbol=symbol,
            attempts=[
                ProviderAttempt(
                    "fmp",
                    "FMP",
                    lambda: self._fmp().get_earnings_calendar(symbol, limit) if self._fmp() else None,
                ),
            ],
        )


