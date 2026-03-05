"""Portfolio news impact resource."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

PORTFOLIO_NEWS_IMPACT_URI = "portfolio://news-impact"


def _cache_file_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "cache" / "portfolio_news_impact_latest.json"


def load_cached_result(filename: str) -> str:
    if filename != "portfolio_news_impact_latest.json":
        raise ValueError("Unsupported cache file requested.")
    target = _cache_file_path()
    if not target.exists():
        raise ValueError("Portfolio news impact resource not found. Run get_portfolio_news_impact first.")
    content = target.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("Portfolio news impact resource not found. Run get_portfolio_news_impact first.")
    return content


def register_portfolio_news_impact_resource(mcp: FastMCP) -> None:
    @mcp.resource(
        PORTFOLIO_NEWS_IMPACT_URI,
        name="portfolio-news-impact",
        title="Portfolio News Impact Cache",
        description="Latest news impact analysis result stored after running the portfolio_news_risk workflow.",
        mime_type="application/json",
    )
    def portfolio_news_impact_resource() -> str:
        return load_cached_result("portfolio_news_impact_latest.json")


