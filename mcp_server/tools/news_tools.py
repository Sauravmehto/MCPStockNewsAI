"""News-domain tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.lib.formatters import format_response
from mcp_server.scoring.news_impact_engine import classify_sentiment, is_macro_relevant
from mcp_server.services.base import validate_symbol
from mcp_server.tools.common import ensure_data, format_news_line

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_news_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Get company news headlines.")
    def get_company_news(symbol: str, limit: int = 10) -> str:
        symbol = validate_symbol(symbol)
        result = services.news.get_company_news(symbol, limit=limit)
        items = ensure_data(result.data, result.error)
        lines = [format_news_line(idx + 1, item.headline, item.source, item.datetime, item.url) for idx, item in enumerate(items)]
        return format_response(
            title=f"News for {symbol}",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )

    @mcp.tool(description="Get broad market headlines.")
    def get_market_news(limit: int = 10) -> str:
        result = services.news.get_market_headlines(limit=limit)
        rows = ensure_data(result.data, result.error)
        return format_response(
            title="Market headlines",
            source=result.source,
            warning=result.warning,
            lines=rows,
        )

    @mcp.tool(description="Summarize positive/negative/neutral sentiment from latest headlines for a query.")
    def get_news_sentiment_overview(query: str = "stock market", limit: int = 15) -> str:
        result = services.news.get_company_news(query, limit=limit)
        items = ensure_data(result.data, result.error)
        positive = 0
        negative = 0
        neutral = 0
        sample_lines: list[str] = []
        for idx, item in enumerate(items):
            sentiment = classify_sentiment(item.headline)
            if sentiment > 0:
                positive += 1
                label = "POSITIVE"
            elif sentiment < 0:
                negative += 1
                label = "NEGATIVE"
            else:
                neutral += 1
                label = "NEUTRAL"
            if idx < 5:
                sample_lines.append(f"{idx + 1}. [{label}] {item.headline}")
        lines = [
            f"Query: {query}",
            f"Headlines analyzed: {len(items)}",
            f"Positive: {positive}",
            f"Negative: {negative}",
            f"Neutral: {neutral}",
            "Sample classifications:",
            *sample_lines,
        ]
        return format_response(
            title=f"News sentiment overview for {query}",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )

    @mcp.tool(description="Get macro-sensitive headlines (inflation/rates/Fed/tariffs/recession and related topics).")
    def get_macro_risk_news(limit: int = 10) -> str:
        fetch_limit = max(10, limit * 3)
        result = services.news.get_market_headlines(limit=fetch_limit)
        rows = ensure_data(result.data, result.error)
        macro_rows = [line for line in rows if is_macro_relevant(str(line))]
        selected = macro_rows[:limit] if macro_rows else rows[:limit]
        lines = [*selected]
        if not macro_rows:
            lines.insert(0, "No strictly macro-tagged headlines found; showing latest market headlines instead.")
        return format_response(
            title="Macro risk headlines",
            source=result.source,
            warning=result.warning,
            lines=lines,
        )


