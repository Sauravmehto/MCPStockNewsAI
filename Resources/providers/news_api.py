"""NewsAPI adapter."""

from __future__ import annotations

from urllib.parse import urlencode

from mcp_server.providers.http import fetch_json
from mcp_server.providers.models import NormalizedNewsItem


class NewsApiClient:
    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.base = "https://newsapi.org/v2/everything"

    def get_company_news(self, symbol_or_query: str, limit: int = 10) -> list[NormalizedNewsItem] | None:
        query = urlencode(
            {
                "q": symbol_or_query,
                "sortBy": "publishedAt",
                "pageSize": max(1, min(limit, 50)),
                "apiKey": self.api_key,
            }
        )
        url = f"{self.base}?{query}"
        data = fetch_json(
            url,
            provider="newsapi",
            timeout_seconds=self.timeout_seconds,
            headers={"X-Api-Key": self.api_key},
        )
        articles = (data or {}).get("articles") if isinstance(data, dict) else None
        if not isinstance(articles, list):
            return None
        out: list[NormalizedNewsItem] = []
        for article in articles[:limit]:
            if not isinstance(article, dict):
                continue
            out.append(
                NormalizedNewsItem(
                    headline=str(article.get("title") or "Untitled"),
                    summary=article.get("description"),
                    url=article.get("url"),
                    source=((article.get("source") or {}).get("name") if isinstance(article.get("source"), dict) else None),
                    datetime=None,
                )
            )
        return out or None


