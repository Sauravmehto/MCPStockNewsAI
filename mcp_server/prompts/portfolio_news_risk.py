"""Portfolio news risk prompt definition."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_portfolio_news_risk_prompt(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="portfolio_news_risk",
        title="Portfolio News Risk Prompt",
        description="Analyze current news impact on a portfolio and rank stocks by risk.",
    )
    def portfolio_news_risk(symbols: str, news: str = "") -> str:
        cleaned_symbols = ",".join(part.strip().upper() for part in symbols.split(",") if part.strip())
        if not cleaned_symbols:
            raise ValueError("Missing required argument: symbols.")
        symbols_list_literal = ", ".join(f"'{symbol}'" for symbol in cleaned_symbols.split(","))
        news_literal = news.strip() if news.strip() else "[]"
        if news.strip():
            news_literal = f"['{news.strip()}']"
        return (
            "You are a portfolio risk analyst. Analyze news impact on this portfolio.\n\n"
            "Run tools in this exact order:\n"
            "1) get_market_news(limit=15)\n"
            "2) get_sector_performance()\n"
            f"3) get_watchlist_summary(symbols=[{symbols_list_literal}])\n"
            f"4) get_company_news(symbol) for EACH symbol in [{symbols_list_literal}]\n"
            "5) get_portfolio_news_impact(\n"
            f"       symbols=[{symbols_list_literal}],\n"
            f"       news_items={news_literal},\n"
            "       include_live_news=True\n"
            "   )\n\n"
            "Then produce a structured report:\n"
            "- SECTION 1: Today's macro news summary\n"
            "- SECTION 2: Per-stock news & sentiment\n"
            "- SECTION 3: Risk ranking table (1=most at risk)\n"
            "- SECTION 4: Estimated $ and % portfolio impact\n"
            "- SECTION 5: Recommended actions per holding\n\n"
            "After running the workflow, latest JSON is available at resource: portfolio://news-impact"
        )


