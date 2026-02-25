"""News-domain service."""

from __future__ import annotations

from mcp_server.providers.news_api import NewsApiClient
from mcp_server.providers.yahoo_finance import YahooFinanceClient
from mcp_server.services.base import ServiceContext, ServiceResult, execute_with_fallback


class NewsService:
    def __init__(self, ctx: ServiceContext) -> None:
        self.ctx = ctx

    def _newsapi(self) -> NewsApiClient | None:
        c = self.ctx.get_provider("newsapi")
        return c if isinstance(c, NewsApiClient) else None

    def _yahoo(self) -> YahooFinanceClient | None:
        c = self.ctx.get_provider("yahoo")
        return c if isinstance(c, YahooFinanceClient) else None

    def get_company_news(self, symbol_or_query: str, limit: int = 10):
        return execute_with_fallback(
            "get_company_news",
            [
                ("News API", lambda: self._newsapi().get_company_news(symbol_or_query, limit) if self._newsapi() else None),
                ("Yahoo Finance", lambda: self._yahoo().get_news(symbol_or_query, limit) if self._yahoo() else None),
            ],
            self.ctx,
        )

    def get_market_headlines(self, limit: int = 10) -> ServiceResult[list[str]]:
        result = self.get_company_news("stock market", limit=limit)
        if not result.data:
            return ServiceResult(data=None, source=result.source, warning=result.warning, error=result.error)
        lines = [f"{idx + 1}. {item.headline}" for idx, item in enumerate(result.data[:limit])]
        return ServiceResult(data=lines, source=result.source, warning=result.warning)


