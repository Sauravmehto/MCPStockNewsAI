import asyncio
from types import SimpleNamespace

from mcp.server.fastmcp import FastMCP

from mcp_server.providers.models import NormalizedNewsItem
from mcp_server.services.base import ServiceResult
from mcp_server.tools.news_tools import register_news_tools


class _MockNewsService:
    def get_company_news(self, symbol_or_query: str, limit: int = 10) -> ServiceResult[list[NormalizedNewsItem]]:
        items = [
            NormalizedNewsItem(headline=f"{symbol_or_query} reports strong growth and record demand", source="unit-test"),
            NormalizedNewsItem(headline=f"{symbol_or_query} faces weak demand and warning", source="unit-test"),
            NormalizedNewsItem(headline=f"{symbol_or_query} maintains steady outlook", source="unit-test"),
        ]
        return ServiceResult(data=items[:limit], source="unit-test")

    def get_market_headlines(self, limit: int = 10) -> ServiceResult[list[str]]:
        rows = [
            "Fed signals interest rate path remains restrictive",
            "CPI inflation cools slightly this month",
            "Tech shares mixed after earnings updates",
        ]
        return ServiceResult(data=rows[:limit], source="unit-test")


def _call_tool_result_string(mcp: FastMCP, name: str, arguments: dict[str, object]) -> str:
    _, metadata = asyncio.run(mcp.call_tool(name, arguments))
    return str(metadata.get("result") or "")


def test_news_sentiment_overview_includes_counts() -> None:
    mcp = FastMCP(name="news-tools-sentiment")
    services = SimpleNamespace(news=_MockNewsService())
    register_news_tools(mcp, services)

    result_text = _call_tool_result_string(
        mcp,
        "get_news_sentiment_overview",
        {"query": "AAPL", "limit": 10},
    )
    assert "News sentiment overview for AAPL" in result_text
    assert "Positive: 1" in result_text
    assert "Negative: 1" in result_text
    assert "Neutral: 1" in result_text


def test_macro_risk_news_filters_headlines() -> None:
    mcp = FastMCP(name="news-tools-macro")
    services = SimpleNamespace(news=_MockNewsService())
    register_news_tools(mcp, services)

    result_text = _call_tool_result_string(
        mcp,
        "get_macro_risk_news",
        {"limit": 5},
    )
    assert "Macro risk headlines" in result_text
    assert "interest rate" in result_text
    assert "inflation" in result_text

