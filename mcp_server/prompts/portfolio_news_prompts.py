"""Portfolio news impact prompt definitions."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_portfolio_news_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="portfolio_news_risk",
        title="Portfolio News Risk Prompt",
        description="Generate exact workflow steps for portfolio news impact scoring and ranked risk review.",
    )
    def portfolio_news_risk(
        symbols: list[str],
        quantities: dict[str, float],
        news_items: list[str],
        include_live_news: bool = True,
    ) -> str:
        if not symbols:
            raise ValueError("Missing required argument: symbols.")
        if not quantities:
            raise ValueError("Missing required argument: quantities.")
        symbols_text = ", ".join(symbols)
        return (
            "You are a portfolio risk analyst focused on event-driven downside protection.\n"
            "Execute the following sequence exactly and do not skip steps:\n"
            f"1) get_portfolio_news_impact(symbols={symbols}, quantities={quantities}, news_items={news_items}, include_live_news={include_live_news})\n"
            "2) Read resource portfolio://news-impact to verify cached output and latest ranking payload.\n"
            "3) Rank positions by weighted_risk_score from highest to lowest.\n"
            "4) For each position, report sentiment, relevance, estimated_percent_impact, estimated_dollar_impact, and action.\n"
            "5) End with portfolio-level action priorities and immediate monitoring plan.\n"
            f"Portfolio symbols to analyze: {symbols_text}."
        )


