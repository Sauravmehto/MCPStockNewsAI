"""MCP prompts for stock and portfolio workflows."""

from __future__ import annotations

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from mcp_server.prompts.time_utils import get_unix_range


def _require_text(name: str, value: str) -> str:
    clean = value.strip()
    if not clean:
        raise ValueError(f"Missing required argument: {name}")
    return clean


def _date_range(days_back: int) -> tuple[str, str]:
    unix_range = get_unix_range(days_back)
    from_date = datetime.fromtimestamp(unix_range["from_unix"], tz=timezone.utc).strftime("%Y-%m-%d")
    to_date = datetime.fromtimestamp(unix_range["to_unix"], tz=timezone.utc).strftime("%Y-%m-%d")
    return from_date, to_date


def register_market_prompts(mcp: FastMCP) -> None:
    """Register all production MCP prompts for MCPStocknewsAI."""

    @mcp.prompt(name="stock_full_analysis", description="Complete technical, fundamental, and sentiment analysis for a US stock")
    def stock_full_analysis(symbol: str, interval: str = "1d", period: int = 30) -> str:
        """Build the stock_full_analysis prompt message."""
        symbol = _require_text("symbol", symbol)
        unix_range = get_unix_range(period)
        from_date, to_date = _date_range(period)
        return (
            f"Run a full analysis for {symbol}. Call tools in this exact order and do not skip steps.\n"
            "1) get_stock_price(symbol)\n"
            "2) get_quote(symbol)\n"
            "3) get_company_profile(symbol)\n"
            "4) get_key_financials(symbol)\n"
            "5) get_fundamental_ratings(symbol)\n"
            "6) get_financial_statements(symbol)\n"
            f"7) get_rsi(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"8) get_macd(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"9) get_sma(symbol='{symbol}', interval='{interval}', period=20, from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"10) get_ema(symbol='{symbol}', interval='{interval}', period=20, from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"11) get_support_resistance_levels(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"12) detect_chart_patterns(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            "13) get_price_targets(symbol)\n"
            "14) get_ownership_signals(symbol)\n"
            f"15) get_stock_news(symbol='{symbol}', from_date='{from_date}', to_date='{to_date}')\n"
            "16) get_company_news(symbol)\n"
            "Return a structured report with sections: Price Summary, Fundamentals, Technical Analysis, "
            "Chart Patterns, Analyst Targets, Ownership, News Sentiment."
        )

    @mcp.prompt(name="market_morning_brief", description="Complete pre-market overview of US market conditions to start the trading day")
    def market_morning_brief() -> str:
        """Build the market_morning_brief prompt message."""
        return (
            "Create a morning market briefing. Call tools in this exact order:\n"
            "1) get_market_status()\n"
            "2) get_market_indices()\n"
            "3) get_vix()\n"
            "4) get_sector_performance()\n"
            "5) get_market_breadth()\n"
            "6) get_market_movers(kind='gainers')\n"
            "7) get_market_movers(kind='losers')\n"
            "8) get_market_movers(kind='active')\n"
            "9) get_market_news(limit=10)\n"
            "Output must include market status, index levels, VIX risk tone, sector leaders/laggards, movers, and headlines."
        )

    @mcp.prompt(name="earnings_preview", description="Deep pre-earnings analysis before a company reports results")
    def earnings_preview(symbol: str) -> str:
        """Build the earnings_preview prompt message."""
        symbol = _require_text("symbol", symbol)
        from_date, to_date = _date_range(30)
        return (
            f"Prepare pre-earnings analysis for {symbol}. Call tools in this exact order:\n"
            "1) get_earnings_calendar(symbol)\n"
            "2) get_key_financials(symbol)\n"
            "3) get_financial_statements(symbol, statementType='income', period='annual')\n"
            "4) get_financial_statements(symbol, statementType='income', period='quarterly')\n"
            "5) get_price_targets(symbol)\n"
            "6) get_options_iv(symbol)\n"
            "7) get_options_chain(symbol)\n"
            "8) get_max_pain(symbol)\n"
            "9) get_unusual_options_activity(symbol)\n"
            f"10) get_stock_news(symbol='{symbol}', from_date='{from_date}', to_date='{to_date}')\n"
            "Output: earnings date, IV-implied move, EPS trend, analyst targets, options positioning, max pain, sentiment."
        )

    @mcp.prompt(name="portfolio_full_review", description="Comprehensive health check and risk analysis of an entire portfolio from Excel file")
    def portfolio_full_review(file_path: str) -> str:
        """Build the portfolio_full_review prompt message."""
        file_path = _require_text("file_path", file_path)
        return (
            f"Run a complete portfolio review for file_path='{file_path}'. Call tools in this exact order:\n"
            "1) validate_portfolio_excel(file_path)\n"
            "2) analyze_portfolio_excel(file_path, include_ai_summary=true)\n"
            "3) portfolio_benchmark_report(file_path)\n"
            "4) portfolio_stress_test(file_path)\n"
            "Output validation summary, analytics, benchmark comparison, stress scenarios, and AI summary."
        )

    @mcp.prompt(name="options_deep_dive", description="Full options market analysis including flow, Greeks, IV and max pain")
    def options_deep_dive(symbol: str) -> str:
        """Build the options_deep_dive prompt message."""
        symbol = _require_text("symbol", symbol)
        return (
            f"Perform options deep dive for {symbol}. Call tools in this exact order:\n"
            "1) get_stock_price(symbol)\n"
            "2) get_options_chain(symbol)\n"
            "3) get_options_greeks(symbol)\n"
            "4) get_options_iv(symbol)\n"
            "5) get_max_pain(symbol)\n"
            "6) get_unusual_options_activity(symbol)\n"
            "Output: price context, chain summary, Greeks, IV, max pain, unusual flow with bullish/bearish bias."
        )

    @mcp.prompt(name="risk_profile", description="Complete downside risk and volatility assessment for a position")
    def risk_profile(symbol: str, benchmark_symbol: str = "SPY", interval: str = "1d") -> str:
        """Build the risk_profile prompt message."""
        symbol = _require_text("symbol", symbol)
        benchmark_symbol = _require_text("benchmark_symbol", benchmark_symbol)
        unix_range = get_unix_range(30)
        return (
            f"Assess risk for {symbol}. Call tools in this exact order:\n"
            f"1) get_var(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']}, confidence=0.95)\n"
            f"2) get_max_drawdown(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"3) get_beta(symbol='{symbol}', benchmark_symbol='{benchmark_symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"4) get_sharpe_sortino(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"5) get_options_iv(symbol='{symbol}')\n"
            f"6) get_correlation(symbol='{symbol}', peer_symbol='{benchmark_symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            "Output: VaR, max drawdown, beta, Sharpe/Sortino, IV, and market correlation."
        )

    @mcp.prompt(name="dividend_income_analysis", description="Full dividend analysis and income projection for a dividend-paying stock")
    def dividend_income_analysis(symbol: str, shares: float, annual_dividend_per_share: float) -> str:
        """Build the dividend_income_analysis prompt message."""
        symbol = _require_text("symbol", symbol)
        return (
            f"Run dividend income analysis for {symbol}. Call tools in this exact order:\n"
            "1) get_dividends(symbol)\n"
            "2) get_splits(symbol)\n"
            "3) get_key_financials(symbol)\n"
            "4) get_financial_statements(symbol, statementType='cashflow')\n"
            f"5) get_dividend_projection(annualDividendPerShare={annual_dividend_per_share}, shares={shares})\n"
            "Output: dividend history, split history, payout sustainability, annual/monthly income projection."
        )

    @mcp.prompt(name="stock_screener_analysis", description="Screen and analyze a list of stocks against filters then rank results")
    def stock_screener_analysis(symbols: str, sector: str = "", min_price: float | None = None, max_price: float | None = None) -> str:
        """Build the stock_screener_analysis prompt message."""
        symbols = _require_text("symbols", symbols)
        return (
            "Run screener analysis. Call tools in this exact order:\n"
            f"1) run_screener(symbols={symbols.split(',')}, sector='{sector}', minPrice={min_price}, maxPrice={max_price})\n"
            "2) For each resulting symbol call get_fundamental_ratings(symbol)\n"
            "3) For each resulting symbol call get_rsi(symbol, interval='1d', from_unix, to_unix)\n"
            "4) For each resulting symbol call get_price_targets(symbol)\n"
            "Output a ranked table by overall score."
        )

    @mcp.prompt(name="sector_rotation_analysis", description="Identify sector momentum shifts and rotation opportunities")
    def sector_rotation_analysis() -> str:
        """Build the sector_rotation_analysis prompt message."""
        return (
            "Run sector rotation analysis. Call tools in this exact order:\n"
            "1) get_sector_performance()\n"
            "2) get_market_breadth()\n"
            "3) get_market_indices()\n"
            "4) get_vix()\n"
            "5) get_market_movers(kind='gainers')\n"
            "6) get_market_movers(kind='losers')\n"
            "Output sector ranking, breadth quality, rotation candidates, and risk-on/risk-off interpretation."
        )

    @mcp.prompt(name="stock_compare", description="Side-by-side comparison of two US stocks across technicals and fundamentals")
    def stock_compare(symbol1: str, symbol2: str) -> str:
        """Build the stock_compare prompt message."""
        symbol1 = _require_text("symbol1", symbol1)
        symbol2 = _require_text("symbol2", symbol2)
        unix_range = get_unix_range(30)
        return (
            f"Compare {symbol1} vs {symbol2}. Run each symbol in parallel with the same sequence:\n"
            "1) get_quote(symbol)\n"
            "2) get_key_financials(symbol)\n"
            "3) get_fundamental_ratings(symbol)\n"
            f"4) get_rsi(symbol, interval='1d', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            "5) get_price_targets(symbol)\n"
            f"6) get_beta(symbol, benchmark_symbol='SPY', interval='1d', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            "7) get_ownership_signals(symbol)\n"
            "Output a side-by-side table covering valuation, momentum, analyst view, risk, and ownership."
        )

    @mcp.prompt(name="smart_rebalance", description="Optimize and rebalance a portfolio using Markowitz allocation")
    def smart_rebalance(file_path: str, risk_aversion: float = 1.0) -> str:
        """Build the smart_rebalance prompt message."""
        file_path = _require_text("file_path", file_path)
        return (
            f"Run smart rebalance for file_path='{file_path}'. Call tools in this exact order:\n"
            "1) validate_portfolio_excel(file_path)\n"
            "2) analyze_portfolio_excel(file_path)\n"
            f"3) get_markowitz_allocation(expectedReturns, riskAversion={risk_aversion})\n"
            "4) get_rebalance_plan(currentWeights, targetWeights)\n"
            "5) portfolio_stress_test(file_path)\n"
            "Output current allocation, optimized weights, rebalance actions, and stress-test results."
        )

    @mcp.prompt(name="tax_impact_analysis", description="Estimate tax liability from selling a position")
    def tax_impact_analysis(symbol: str, shares: float, buy_price: float, tax_rate: float, current_price: float | None = None) -> str:
        """Build the tax_impact_analysis prompt message."""
        symbol = _require_text("symbol", symbol)
        return (
            f"Run tax impact analysis for {symbol}. Call tools in this exact order:\n"
            "1) get_stock_price(symbol)\n"
            "2) get_splits(symbol)\n"
            "3) get_tax_estimate(realizedGain, taxRate)\n"
            f"Use shares={shares}, buy_price={buy_price}, tax_rate={tax_rate}, current_price_override={current_price} if provided.\n"
            "Output current price, split-adjusted basis, realized gain, tax estimate, and net proceeds."
        )

    @mcp.prompt(name="insider_institutional_check", description="Analyze insider and institutional ownership signals for a stock")
    def insider_institutional_check(symbol: str) -> str:
        """Build the insider_institutional_check prompt message."""
        symbol = _require_text("symbol", symbol)
        from_date, to_date = _date_range(30)
        return (
            f"Run insider/institutional check for {symbol}. Call tools in this exact order:\n"
            "1) get_ownership_signals(symbol)\n"
            "2) get_sec_filings(symbol)\n"
            "3) get_fundamental_ratings(symbol)\n"
            "4) get_price_targets(symbol)\n"
            f"5) get_stock_news(symbol='{symbol}', from_date='{from_date}', to_date='{to_date}')\n"
            "Output ownership concentration, insider/institutional activity, ratings, targets, and news context."
        )

    @mcp.prompt(name="technical_momentum_scan", description="Quick momentum and trend scan using multiple technical indicators")
    def technical_momentum_scan(symbol: str, interval: str = "1d") -> str:
        """Build the technical_momentum_scan prompt message."""
        symbol = _require_text("symbol", symbol)
        unix_range = get_unix_range(30)
        return (
            f"Run technical momentum scan for {symbol}. Call tools in this exact order:\n"
            f"1) get_candles(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"2) get_rsi(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"3) get_macd(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"4) get_sma(symbol='{symbol}', interval='{interval}', period=20, from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"5) get_sma(symbol='{symbol}', interval='{interval}', period=50, from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"6) get_ema(symbol='{symbol}', interval='{interval}', period=9, from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"7) get_ema(symbol='{symbol}', interval='{interval}', period=21, from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"8) get_support_resistance_levels(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            f"9) detect_chart_patterns(symbol='{symbol}', interval='{interval}', from_unix={unix_range['from_unix']}, to_unix={unix_range['to_unix']})\n"
            "Output trend direction, RSI zone, MACD signal, MA context, support/resistance, and pattern bias."
        )


