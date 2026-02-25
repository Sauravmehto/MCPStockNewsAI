"""Portfolio prompt definitions."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def _build_portfolio_analysis_prompt(portfolio: str) -> str:
    portfolio_name = portfolio.strip()
    if not portfolio_name:
        raise ValueError("Missing required argument: portfolio.")
    return (
        "You are an institutional portfolio analyst.\n"
        f"Analyze the portfolio named '{portfolio_name}' and provide:\n"
        "1) Allocation diagnostics (overweight/underweight and concentration)\n"
        "2) Key risk findings (beta, volatility, drawdown, VaR)\n"
        "3) Benchmark-relative interpretation\n"
        "4) A concise action plan with priorities."
    )


def register_portfolio_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="portfolio_analysis",
        title="Portfolio Analysis Prompt",
        description="Generate a structured analysis prompt for a named portfolio.",
    )
    def portfolio_analysis(portfolio: str) -> str:
        return _build_portfolio_analysis_prompt(portfolio)


