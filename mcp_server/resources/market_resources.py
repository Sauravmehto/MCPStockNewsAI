"""Market-focused MCP resource registrations."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from mcp_server.protocol.compliance import ProtocolCompliance
    from mcp_server.tools.registry import ToolServices


MARKET_DISCLAIMER_URI = "market://disclaimer"
US_MARKET_HOURS_URI = "market://us-market-hours"
HOLIDAYS_URI = "market://holidays-2025-2026"
SECTOR_MAP_URI = "market://sector-map"
GLOSSARY_URI = "market://glossary"
TOP_SYMBOLS_URI = "market://top-us-symbols"
RISK_THRESHOLDS_URI = "market://risk-thresholds"
PROMPT_GUIDE_URI = "market://prompt-guide"
NEWS_TEMPLATE_URI = "market://news/{symbol}"


STATIC_RESOURCES: dict[str, dict[str, object]] = {
    MARKET_DISCLAIMER_URI: {
        "name": "Legal Disclaimer",
        "mime_type": "text/plain",
        "content": (
            "Data provided by MCPStocknewsAI is for informational purposes only and does not constitute financial advice, "
            "investment recommendations, or an offer to buy or sell any security. Past performance is not indicative of "
            "future results. Users should consult a licensed financial advisor before making any investment decisions. "
            "MCPStocknewsAI is not liable for any trading losses."
        ),
    },
    US_MARKET_HOURS_URI: {
        "name": "US Market Hours",
        "mime_type": "application/json",
        "content": {
            "timezone": "America/New_York",
            "exchanges": ["NYSE", "NASDAQ"],
            "regular_hours": "09:30-16:00",
            "pre_market": "04:00-09:30",
            "after_hours": "16:00-20:00",
        },
    },
    HOLIDAYS_URI: {
        "name": "US Stock Market Holidays",
        "mime_type": "application/json",
        "content": [
            {"date": "2025-01-01", "holiday_name": "New Year's Day"},
            {"date": "2025-01-20", "holiday_name": "Martin Luther King Jr. Day"},
            {"date": "2025-02-17", "holiday_name": "Washington's Birthday"},
            {"date": "2025-04-18", "holiday_name": "Good Friday"},
            {"date": "2025-05-26", "holiday_name": "Memorial Day"},
            {"date": "2025-06-19", "holiday_name": "Juneteenth"},
            {"date": "2025-07-04", "holiday_name": "Independence Day"},
            {"date": "2025-09-01", "holiday_name": "Labor Day"},
            {"date": "2025-11-27", "holiday_name": "Thanksgiving Day"},
            {"date": "2025-12-25", "holiday_name": "Christmas Day"},
            {"date": "2026-01-01", "holiday_name": "New Year's Day"},
            {"date": "2026-01-19", "holiday_name": "Martin Luther King Jr. Day"},
            {"date": "2026-02-16", "holiday_name": "Washington's Birthday"},
            {"date": "2026-04-03", "holiday_name": "Good Friday"},
            {"date": "2026-05-25", "holiday_name": "Memorial Day"},
            {"date": "2026-06-19", "holiday_name": "Juneteenth"},
            {"date": "2026-07-03", "holiday_name": "Independence Day (Observed)"},
            {"date": "2026-09-07", "holiday_name": "Labor Day"},
            {"date": "2026-11-26", "holiday_name": "Thanksgiving Day"},
            {"date": "2026-12-25", "holiday_name": "Christmas Day"},
        ],
    },
    SECTOR_MAP_URI: {
        "name": "S&P 500 Sector Map",
        "mime_type": "application/json",
        "content": {
            "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "CSCO", "AMD", "INTC", "QCOM", "TXN", "NOW", "IBM", "MU"],
            "Healthcare": ["UNH", "JNJ", "LLY", "PFE", "MRK", "ABBV", "TMO", "DHR", "BMY", "AMGN", "CVS", "CI", "GILD", "ISRG", "SYK"],
            "Financials": ["JPM", "BRK.B", "BAC", "WFC", "C", "GS", "MS", "SCHW", "AXP", "BLK", "SPGI", "CB", "PGR", "AIG", "USB"],
            "Energy": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "KMI", "OXY", "HAL", "BKR", "WMB", "DVN", "FANG"],
            "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "BKNG", "TGT", "GM", "F", "MAR", "CMG", "ROST", "AZO"],
            "Industrials": ["GE", "CAT", "UNP", "RTX", "HON", "UPS", "BA", "DE", "LMT", "NOC", "ETN", "MMM", "GD", "FDX", "EMR"],
            "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "EA", "WBD", "FOXA", "PARA", "OMC", "IPG"],
            "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PEG", "ED", "EIX", "WEC", "ES", "AEE", "CNP"],
            "Materials": ["LIN", "APD", "SHW", "ECL", "NEM", "FCX", "DOW", "DD", "CTVA", "PPG", "ALB", "IFF", "VMC", "MLM", "NUE"],
            "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "O", "SPG", "WELL", "DLR", "VICI", "SBAC", "AVB", "EQR", "EXR", "ESS"],
            "Consumer Staples": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "MDLZ", "KMB", "GIS", "KHC", "SYY", "KR", "MNST"],
        },
    },
    GLOSSARY_URI: {
        "name": "Financial & Technical Analysis Glossary",
        "mime_type": "application/json",
        "content": {
            "RSI": "Momentum oscillator measuring speed of price changes (0-100).",
            "MACD": "Trend-following momentum indicator based on EMA spreads.",
            "EMA": "Exponential moving average weighting recent prices more heavily.",
            "SMA": "Simple moving average using equal-weighted period prices.",
            "Beta": "Sensitivity of asset returns versus benchmark returns.",
            "Sharpe Ratio": "Excess return per unit of total volatility.",
            "Sortino Ratio": "Excess return per unit of downside volatility.",
            "VaR": "Estimated loss threshold for a confidence interval over a period.",
            "Max Drawdown": "Largest peak-to-trough decline in a series.",
            "Implied Volatility": "Option-implied expected volatility over life of contract.",
            "Max Pain": "Strike where aggregate option holder losses are maximized.",
            "Support": "Price area where buying interest often appears.",
            "Resistance": "Price area where selling pressure often appears.",
            "P/E Ratio": "Price divided by earnings per share.",
            "EPS": "Earnings per share.",
            "Market Cap": "Share price multiplied by shares outstanding.",
            "Float": "Shares available for public trading.",
            "Short Interest": "Open short positions in a security.",
            "Delta": "Option price sensitivity to underlying move.",
            "Gamma": "Rate of change of option delta.",
            "Theta": "Option time decay sensitivity.",
            "Vega": "Option price sensitivity to implied volatility changes.",
            "Markowitz Allocation": "Mean-variance portfolio optimization weighting.",
            "Drawdown": "Decline from prior peak value.",
            "Dividend Yield": "Annual dividend divided by share price.",
            "Payout Ratio": "Dividends paid as a proportion of earnings.",
            "10-K": "Annual SEC report.",
            "10-Q": "Quarterly SEC report.",
            "8-K": "Current report for material events.",
            "13F": "Quarterly institutional holdings report.",
        },
    },
    TOP_SYMBOLS_URI: {
        "name": "Top Watched US Symbols",
        "mime_type": "application/json",
        "content": {
            "mega_cap": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRKA", "JPM", "V", "UNH", "XOM"],
            "sp500_etfs": ["SPY", "IVV", "VOO"],
            "nasdaq_etfs": ["QQQ", "QQQM"],
            "broad_etfs": ["IWM", "DIA", "VTI"],
            "sector_etfs": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLC", "XLU", "XLB", "XLRE", "XLP"],
            "volatility": ["VIX", "UVXY", "SVXY"],
            "commodities": ["GLD", "SLV", "USO", "UNG"],
            "bonds": ["TLT", "IEF", "SHY", "HYG"],
            "popular_individual": ["TSLA", "NVDA", "AMD", "PLTR", "SOFI", "GME", "COIN", "MSTR"],
        },
    },
    RISK_THRESHOLDS_URI: {
        "name": "Risk Level Classification Thresholds",
        "mime_type": "application/json",
        "content": {
            "beta_vs_spy": {"low": "<0.8", "medium": "0.8-1.2", "high": "1.2-1.7", "very_high": ">1.7"},
            "var_95_percent": {"low": "<1.5%", "medium": "1.5%-3%", "high": "3%-5%", "very_high": ">5%"},
            "iv_percentile": {"low": "<25", "medium": "25-50", "high": "50-75", "very_high": ">75"},
            "rsi": {"oversold": "<30", "neutral": "30-70", "overbought": ">70"},
            "max_drawdown_percent": {"low": "<10%", "medium": "10%-20%", "high": "20%-35%", "very_high": ">35%"},
            "sharpe_ratio": {"excellent": ">2.0", "good": "1.0-2.0", "fair": "0-1.0", "poor": "<0"},
            "correlation": {"low": "<0.3", "medium": "0.3-0.7", "high": ">0.7"},
        },
    },
}


PROMPT_GUIDE_TEXT = """Available MCPStocknewsAI prompts:
- stock_full_analysis(symbol, interval='1d', period=30)
- market_morning_brief()
- earnings_preview(symbol)
- portfolio_full_review(file_path)
- options_deep_dive(symbol)
- risk_profile(symbol, benchmark_symbol='SPY', interval='1d')
- dividend_income_analysis(symbol, shares, annual_dividend_per_share)
- stock_screener_analysis(symbols, sector='', min_price=None, max_price=None)
- sector_rotation_analysis()
- stock_compare(symbol1, symbol2)
- smart_rebalance(file_path, risk_aversion=1.0)
- tax_impact_analysis(symbol, shares, buy_price, tax_rate, current_price=None)
- insider_institutional_check(symbol)
- technical_momentum_scan(symbol, interval='1d')
Use prompts/get with arguments and then follow tool sequence exactly as generated.
"""


class MarketNewsPoller:
    """Poll subscribed market news resources and notify clients on change."""

    def __init__(self, services: "ToolServices", protocol: "ProtocolCompliance", poll_seconds: int = 300) -> None:
        self.services = services
        self.protocol = protocol
        self.poll_seconds = max(60, poll_seconds)
        self._stop_event = threading.Event()
        self._latest_hash: dict[str, str] = {}
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            uris = self.protocol.get_subscribed_uris(prefix="market://news/")
            for uri in uris:
                symbol = uri.split("/")[-1].upper().strip()
                if not symbol:
                    continue
                result = self.services.news.get_company_news(symbol, limit=10)
                rows = [asdict(item) for item in (result.data or [])]
                digest = json.dumps(rows, ensure_ascii=True)
                prior = self._latest_hash.get(uri)
                if prior is None:
                    self._latest_hash[uri] = digest
                    continue
                if digest != prior:
                    self._latest_hash[uri] = digest
                    self.protocol.notify_resource_updated_sync(uri)
            self._stop_event.wait(self.poll_seconds)


def register_market_resources(mcp: FastMCP, services: "ToolServices", protocol: "ProtocolCompliance") -> None:
    """Register static resources and dynamic market news template resource."""

    if not hasattr(mcp, "_market_news_poller"):
        setattr(mcp, "_market_news_poller", MarketNewsPoller(services=services, protocol=protocol))

    @mcp.resource(
        MARKET_DISCLAIMER_URI,
        name=str(STATIC_RESOURCES[MARKET_DISCLAIMER_URI]["name"]),
        mime_type=str(STATIC_RESOURCES[MARKET_DISCLAIMER_URI]["mime_type"]),
    )
    def market_disclaimer() -> str:
        """Return legal disclaimer text."""
        return str(STATIC_RESOURCES[MARKET_DISCLAIMER_URI]["content"])

    @mcp.resource(
        US_MARKET_HOURS_URI,
        name=str(STATIC_RESOURCES[US_MARKET_HOURS_URI]["name"]),
        mime_type=str(STATIC_RESOURCES[US_MARKET_HOURS_URI]["mime_type"]),
    )
    def us_market_hours() -> str:
        """Return market hours metadata."""
        return json.dumps(STATIC_RESOURCES[US_MARKET_HOURS_URI]["content"], ensure_ascii=True)

    @mcp.resource(HOLIDAYS_URI, name=str(STATIC_RESOURCES[HOLIDAYS_URI]["name"]), mime_type=str(STATIC_RESOURCES[HOLIDAYS_URI]["mime_type"]))
    def market_holidays() -> str:
        """Return official US exchange holidays for 2025-2026."""
        return json.dumps(STATIC_RESOURCES[HOLIDAYS_URI]["content"], ensure_ascii=True)

    @mcp.resource(SECTOR_MAP_URI, name=str(STATIC_RESOURCES[SECTOR_MAP_URI]["name"]), mime_type=str(STATIC_RESOURCES[SECTOR_MAP_URI]["mime_type"]))
    def sector_map() -> str:
        """Return sector map data."""
        return json.dumps(STATIC_RESOURCES[SECTOR_MAP_URI]["content"], ensure_ascii=True)

    @mcp.resource(GLOSSARY_URI, name=str(STATIC_RESOURCES[GLOSSARY_URI]["name"]), mime_type=str(STATIC_RESOURCES[GLOSSARY_URI]["mime_type"]))
    def glossary() -> str:
        """Return finance and technical glossary entries."""
        return json.dumps(STATIC_RESOURCES[GLOSSARY_URI]["content"], ensure_ascii=True)

    @mcp.resource(TOP_SYMBOLS_URI, name=str(STATIC_RESOURCES[TOP_SYMBOLS_URI]["name"]), mime_type=str(STATIC_RESOURCES[TOP_SYMBOLS_URI]["mime_type"]))
    def top_symbols() -> str:
        """Return common US watchlist symbols by category."""
        return json.dumps(STATIC_RESOURCES[TOP_SYMBOLS_URI]["content"], ensure_ascii=True)

    @mcp.resource(
        RISK_THRESHOLDS_URI,
        name=str(STATIC_RESOURCES[RISK_THRESHOLDS_URI]["name"]),
        mime_type=str(STATIC_RESOURCES[RISK_THRESHOLDS_URI]["mime_type"]),
    )
    def risk_thresholds() -> str:
        """Return risk threshold configuration."""
        return json.dumps(STATIC_RESOURCES[RISK_THRESHOLDS_URI]["content"], ensure_ascii=True)

    @mcp.resource(PROMPT_GUIDE_URI, name="MCPStocknewsAI Prompt Usage Guide", mime_type="text/plain")
    def prompt_guide() -> str:
        """Return plain text prompt usage guide."""
        return PROMPT_GUIDE_TEXT

    @mcp.resource(NEWS_TEMPLATE_URI, name="Live Stock News Feed", description="Latest news headlines for any US stock symbol", mime_type="application/json")
    def market_news(symbol: str) -> str:
        """Return latest company news for a symbol from existing get_company_news pipeline."""
        clean_symbol = symbol.strip().upper()
        if not clean_symbol:
            raise ValueError("Resource not found for empty symbol.")
        result = services.news.get_company_news(clean_symbol, limit=10)
        rows = [asdict(item) for item in (result.data or [])]
        return json.dumps({"symbol": clean_symbol, "headlines": rows}, ensure_ascii=True)


