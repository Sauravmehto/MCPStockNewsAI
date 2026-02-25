"""Manual MCP prompts/resources smoke test for MCPStocknewsAI."""

from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.config.settings import get_settings
from mcp_server.main import resolve_http_transport, resolve_transport_mode
from mcp_server.prompts.market_prompts import register_market_prompts
from mcp_server.prompts.portfolio_prompts import register_portfolio_prompts
from mcp_server.protocol.compliance import configure_protocol_compliance
from mcp_server.providers.alpha_vantage import AlphaVantageClient
from mcp_server.providers.anthropic_client import AnthropicClient
from mcp_server.providers.finnhub import FinnhubClient
from mcp_server.providers.fmp import FmpClient
from mcp_server.providers.fred import FredClient
from mcp_server.providers.marketstack import MarketStackClient
from mcp_server.providers.news_api import NewsApiClient
from mcp_server.providers.sec_edgar import SecEdgarClient
from mcp_server.providers.twelve_data import TwelveDataClient
from mcp_server.providers.web_quote_search import WebQuoteSearchClient
from mcp_server.providers.yahoo_finance import YahooFinanceClient
from mcp_server.resources.market_resources import register_market_resources
from mcp_server.resources.portfolio_resources import register_portfolio_resources
from mcp_server.services.base import ServiceContext
from mcp_server.tools.registry import build_tool_services, register_all_tools
from mcp_server.utils.rate_limit import RateLimiterRegistry


def _status(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}{' - ' + detail if detail else ''}")


def _sample_prompt_args() -> dict[str, dict[str, object]]:
    return {
        "stock_full_analysis": {"symbol": "AAPL"},
        "market_morning_brief": {},
        "earnings_preview": {"symbol": "AAPL"},
        "portfolio_full_review": {"file_path": "test_portfolio.xlsx"},
        "options_deep_dive": {"symbol": "AAPL"},
        "risk_profile": {"symbol": "AAPL"},
        "dividend_income_analysis": {"symbol": "AAPL", "shares": 100, "annual_dividend_per_share": 0.96},
        "stock_screener_analysis": {"symbols": "AAPL,MSFT"},
        "sector_rotation_analysis": {},
        "stock_compare": {"symbol1": "AAPL", "symbol2": "MSFT"},
        "smart_rebalance": {"file_path": "test_portfolio.xlsx"},
        "tax_impact_analysis": {"symbol": "AAPL", "shares": 100, "buy_price": 150, "tax_rate": 0.25},
        "insider_institutional_check": {"symbol": "AAPL"},
        "technical_momentum_scan": {"symbol": "AAPL"},
        "portfolio_analysis": {"portfolio": "US Core"},
    }


TARGET_STATIC_URIS = {
    "market://disclaimer",
    "market://us-market-hours",
    "market://holidays-2025-2026",
    "market://sector-map",
    "market://glossary",
    "market://top-us-symbols",
    "market://risk-thresholds",
    "market://prompt-guide",
}


async def main() -> None:
    settings = get_settings()
    finnhub_client = FinnhubClient(settings.finnhub_api_key, settings.request_timeout_seconds) if settings.finnhub_api_key else None
    alpha_vantage_client = AlphaVantageClient(settings.alphavantage_api_key, settings.request_timeout_seconds) if settings.alphavantage_api_key else None
    yahoo_client = YahooFinanceClient(settings.request_timeout_seconds) if settings.yahoo_finance_enabled else None
    fmp_client = FmpClient(settings.fmp_api_key, settings.request_timeout_seconds) if settings.fmp_api_key else None
    twelvedata_client = TwelveDataClient(settings.twelvedata_api_key, settings.request_timeout_seconds) if settings.twelvedata_api_key else None
    marketstack_client = MarketStackClient(settings.marketstack_api_key, settings.request_timeout_seconds) if settings.marketstack_api_key else None
    web_quote_search_client = WebQuoteSearchClient(settings.request_timeout_seconds)
    fred_client = FredClient(settings.fred_api_key, settings.request_timeout_seconds) if settings.fred_api_key else None
    news_api_client = NewsApiClient(settings.news_api_key, settings.request_timeout_seconds) if settings.news_api_key else None
    sec_client = SecEdgarClient(settings.sec_user_agent, settings.request_timeout_seconds)
    anthropic_client = (
        AnthropicClient(settings.claude_api_key, settings.claude_model, settings.request_timeout_seconds)
        if settings.claude_api_key and settings.portfolio_enable_ai_summary
        else None
    )

    mcp = FastMCP(name=settings.app_name, host=settings.host, port=settings.port, streamable_http_path=settings.mcp_path)
    protocol = configure_protocol_compliance(mcp)
    service_ctx = ServiceContext(
        providers={
            "finnhub": finnhub_client,
            "alphavantage": alpha_vantage_client,
            "yahoo": yahoo_client,
            "fmp": fmp_client,
            "twelvedata": twelvedata_client,
            "marketstack": marketstack_client,
            "websearch": web_quote_search_client,
            "fred": fred_client,
            "newsapi": news_api_client,
            "sec": sec_client,
            "anthropic": anthropic_client,
        },
        cache=TTLCache(default_ttl_seconds=settings.cache_ttl_seconds),
        rate_limiter=RateLimiterRegistry(min_interval_seconds=settings.provider_min_interval_seconds),
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )
    services = build_tool_services(service_ctx, portfolio_enable_ai_summary=settings.portfolio_enable_ai_summary)
    register_all_tools(mcp, services)
    register_market_prompts(mcp)
    register_portfolio_prompts(mcp)
    register_market_resources(mcp, services, protocol)
    register_portfolio_resources(mcp, services)

    print(f"Transport mode: {resolve_transport_mode(settings.transport_mode)} / {resolve_http_transport(settings.http_transport)}")

    prompts = await mcp.list_prompts()
    print("Prompts:")
    for prompt in prompts:
        arg_names = [arg.name for arg in (prompt.arguments or [])]
        print(f"- {prompt.name} args={arg_names}")
    _status("prompts/list", len(prompts) > 0)

    sample_args = _sample_prompt_args()
    for prompt in prompts:
        args = sample_args.get(prompt.name, {})
        try:
            prompt_result = await mcp.get_prompt(prompt.name, args)
            _status(f"prompts/get {prompt.name}", len(prompt_result.messages) > 0)
        except Exception as error:
            _status(f"prompts/get {prompt.name}", False, str(error))

    resources = await mcp.list_resources()
    print("Resources:")
    for resource in resources:
        print(f"- {resource.uri} ({resource.name})")
    _status("resources/list", len(resources) > 0)

    templates = await mcp.list_resource_templates()
    print("Resource templates:")
    for template in templates:
        print(f"- {template.uriTemplate} ({template.name})")
    _status("resources/templates/list", len(templates) > 0)

    for resource in resources:
        if str(resource.uri) not in TARGET_STATIC_URIS:
            continue
        try:
            contents = await mcp.read_resource(str(resource.uri))
            is_non_empty = len(contents) > 0 and bool((contents[0].content or "").strip())
            _status(f"resources/read {resource.uri}", is_non_empty)
        except Exception as error:
            _status(f"resources/read {resource.uri}", False, str(error))

    try:
        news_contents = await mcp.read_resource("market://news/AAPL")
        payload = json.loads(news_contents[0].content)
        headlines = payload.get("headlines") or []
        first_headline = headlines[0]["headline"] if headlines else "<none>"
        print(f"market://news/AAPL first headline: {first_headline}")
        _status("resources/read market://news/AAPL", len(headlines) > 0)
    except Exception as error:
        _status("resources/read market://news/AAPL", False, str(error))


if __name__ == "__main__":
    asyncio.run(main())


