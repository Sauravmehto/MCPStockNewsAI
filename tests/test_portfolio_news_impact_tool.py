import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_server.providers.models import NormalizedCompanyProfile, NormalizedKeyFinancials, NormalizedNewsItem, NormalizedQuote
from mcp_server.services.base import ErrorEnvelope, ServiceResult
from mcp_server.tools.portfolio_news_impact import register_portfolio_news_impact_tools


class _MockCtx:
    def get_provider(self, name: str):  # noqa: ANN001
        return None


class _MockNewsService:
    def __init__(self) -> None:
        self.ctx = _MockCtx()

    def get_company_news(self, symbol: str, limit: int = 10) -> ServiceResult[list[NormalizedNewsItem]]:
        item = NormalizedNewsItem(headline=f"{symbol} faces weak demand and profit warning", source="unit-test", datetime=1700000000)
        return ServiceResult(data=[item], source="unit-test")

    def get_market_headlines(self, limit: int = 10) -> ServiceResult[list[str]]:
        return ServiceResult(data=["Fed warns inflation remains elevated"], source="unit-test")


class _MockStocksService:
    def get_quote(self, symbol: str) -> ServiceResult[NormalizedQuote]:
        return ServiceResult(
            data=NormalizedQuote(
                symbol=symbol,
                price=100.0 if symbol == "AAPL" else 250.0,
                change=0.0,
                percent_change=0.0,
                high=101.0,
                low=99.0,
                open=100.0,
                previous_close=100.0,
                timestamp=1700000000,
                source="finnhub",
            ),
            source="unit-test",
        )

    def get_profile(self, symbol: str) -> ServiceResult[NormalizedCompanyProfile]:
        industry = "technology" if symbol == "AAPL" else "automotive"
        return ServiceResult(data=NormalizedCompanyProfile(symbol=symbol, industry=industry), source="unit-test")


class _MockFundamentalService:
    def get_metrics(self, symbol: str) -> ServiceResult[NormalizedKeyFinancials]:
        beta = 1.1 if symbol == "AAPL" else 2.0
        return ServiceResult(data=NormalizedKeyFinancials(symbol=symbol, beta=beta), source="unit-test")


class _PartiallyFailingStocksService(_MockStocksService):
    def get_quote(self, symbol: str) -> ServiceResult[NormalizedQuote]:
        if symbol == "TSLA":
            return ServiceResult(
                data=None,
                error=ErrorEnvelope(
                    code="UPSTREAM",
                    message="All stock data providers are currently unavailable. Please try again later.",
                ),
                source="unit-test",
            )
        return super().get_quote(symbol)


def _call_tool_result_string(mcp: FastMCP, name: str, arguments: dict[str, object]) -> str:
    _, metadata = asyncio.run(mcp.call_tool(name, arguments))
    return str(metadata.get("result") or "")


def test_portfolio_news_impact_happy_path_ranking_and_cache_write(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_target = tmp_path / "portfolio_news_impact_latest.json"
    monkeypatch.setattr("mcp_server.tools.portfolio_news_impact._cache_file_path", lambda: cache_target)

    mcp = FastMCP(name="portfolio-news-impact-tool")
    services = SimpleNamespace(news=_MockNewsService(), stocks=_MockStocksService(), fundamental=_MockFundamentalService())
    register_portfolio_news_impact_tools(mcp, services)

    payload_text = _call_tool_result_string(
        mcp,
        "get_portfolio_news_impact",
        {
            "symbols": ["AAPL", "TSLA"],
            "news_items": ["TSLA reports weak delivery outlook and warning"],
            "include_live_news": True,
        },
    )
    payload = json.loads(payload_text)
    ranked = payload["ranked_positions"]
    assert len(ranked) == 2
    assert ranked[0]["symbol"] == "TSLA"
    assert "cache_file" in payload
    assert cache_target.exists()
    cached = json.loads(cache_target.read_text(encoding="utf-8"))
    assert "ranked_positions" in cached


def test_portfolio_news_impact_validation_error_for_missing_symbols() -> None:
    mcp = FastMCP(name="portfolio-news-impact-tool-validation")
    services = SimpleNamespace(news=_MockNewsService(), stocks=_MockStocksService(), fundamental=_MockFundamentalService())
    register_portfolio_news_impact_tools(mcp, services)
    with pytest.raises(Exception):
        asyncio.run(
            mcp.call_tool(
                "get_portfolio_news_impact",
                {
                    "symbols": [],
                    "news_items": ["Fed warns inflation risk remains high"],
                    "include_live_news": False,
                },
            )
        )


def test_symbol_news_impact_returns_item_level_payload() -> None:
    mcp = FastMCP(name="symbol-news-impact-tool")
    services = SimpleNamespace(news=_MockNewsService(), stocks=_MockStocksService(), fundamental=_MockFundamentalService())
    register_portfolio_news_impact_tools(mcp, services)

    payload_text = _call_tool_result_string(
        mcp,
        "get_symbol_news_impact",
        {
            "symbol": "AAPL",
            "news_items": ["AAPL receives strong AI demand update"],
            "include_live_news": False,
        },
    )
    payload = json.loads(payload_text)
    assert payload["symbol"] == "AAPL"
    assert payload["news_count"] == 1
    assert payload["summary"]["symbol"] == "AAPL"
    assert len(payload["summary"]["items"]) == 1


def test_watchlist_news_impact_ranks_symbols() -> None:
    mcp = FastMCP(name="watchlist-news-impact-tool")
    services = SimpleNamespace(news=_MockNewsService(), stocks=_MockStocksService(), fundamental=_MockFundamentalService())
    register_portfolio_news_impact_tools(mcp, services)

    payload_text = _call_tool_result_string(
        mcp,
        "get_watchlist_news_impact",
        {
            "symbols": ["TSLA", "AAPL"],
            "include_live_news": True,
        },
    )
    payload = json.loads(payload_text)
    assert payload["input_symbols"] == ["TSLA", "AAPL"]
    assert len(payload["ranked_positions"]) == 2
    assert payload["ranked_positions"][0]["symbol"] == "TSLA"


def test_watchlist_news_impact_skips_symbols_when_quote_unavailable() -> None:
    mcp = FastMCP(name="watchlist-news-impact-partial")
    services = SimpleNamespace(news=_MockNewsService(), stocks=_PartiallyFailingStocksService(), fundamental=_MockFundamentalService())
    register_portfolio_news_impact_tools(mcp, services)

    payload_text = _call_tool_result_string(
        mcp,
        "get_watchlist_news_impact",
        {
            "symbols": ["TSLA", "AAPL"],
            "include_live_news": True,
        },
    )
    payload = json.loads(payload_text)
    assert payload["ok"] is True
    assert payload["processed_count"] == 1
    assert payload["ranked_positions"][0]["symbol"] == "AAPL"
    assert payload["skipped_symbols"][0]["symbol"] == "TSLA"

