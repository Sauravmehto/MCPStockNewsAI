"""Application entrypoint for Local Stock Analyst MCP server."""

from __future__ import annotations

import asyncio
import os

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse, Response

from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.config.settings import get_settings
from mcp_server.providers.alpha_vantage import AlphaVantageClient
from mcp_server.providers.anthropic_client import AnthropicClient
from mcp_server.providers.fmp import FmpClient
from mcp_server.providers.fred import FredClient
from mcp_server.providers.finnhub import FinnhubClient
from mcp_server.providers.marketstack import MarketStackClient
from mcp_server.providers.news_api import NewsApiClient
from mcp_server.providers.sec_edgar import SecEdgarClient
from mcp_server.providers.twelve_data import TwelveDataClient
from mcp_server.providers.web_quote_search import WebQuoteSearchClient
from mcp_server.providers.yahoo_finance import YahooFinanceClient
from mcp_server.services.base import ServiceContext
from mcp_server.tools.registry import build_tool_services, register_all_tools
from mcp_server.utils.rate_limit import RateLimiterRegistry


def resolve_transport_mode(configured_mode: str) -> str:
    if os.getenv("RENDER") and configured_mode == "stdio":
        return "http"
    if configured_mode in {"stdio", "http"}:
        return configured_mode
    if os.getenv("RENDER") or os.getenv("PORT"):
        return "http"
    return "stdio"


def resolve_http_transport(configured_transport: str) -> str:
    if configured_transport in {"sse", "streamable"}:
        return configured_transport
    return "sse"


async def run() -> None:
    settings = get_settings()
    finnhub_client = (
        FinnhubClient(settings.finnhub_api_key, settings.request_timeout_seconds)
        if settings.finnhub_api_key
        else None
    )
    alpha_vantage_client = (
        AlphaVantageClient(settings.alphavantage_api_key, settings.request_timeout_seconds)
        if settings.alphavantage_api_key
        else None
    )
    yahoo_client = YahooFinanceClient(settings.request_timeout_seconds) if settings.yahoo_finance_enabled else None
    fmp_client = FmpClient(settings.fmp_api_key, settings.request_timeout_seconds) if settings.fmp_api_key else None
    twelvedata_client = (
        TwelveDataClient(settings.twelvedata_api_key, settings.request_timeout_seconds)
        if settings.twelvedata_api_key
        else None
    )
    marketstack_client = (
        MarketStackClient(settings.marketstack_api_key, settings.request_timeout_seconds)
        if settings.marketstack_api_key
        else None
    )
    web_quote_search_client = WebQuoteSearchClient(settings.request_timeout_seconds)
    fred_client = FredClient(settings.fred_api_key, settings.request_timeout_seconds) if settings.fred_api_key else None
    news_api_client = (
        NewsApiClient(settings.news_api_key, settings.request_timeout_seconds) if settings.news_api_key else None
    )
    sec_client = SecEdgarClient(settings.sec_user_agent, settings.request_timeout_seconds)
    anthropic_client = (
        AnthropicClient(settings.claude_api_key, settings.claude_model, settings.request_timeout_seconds)
        if settings.claude_api_key and settings.portfolio_enable_ai_summary
        else None
    )
    mcp = FastMCP(
        name=settings.app_name,
        host=settings.host,
        port=settings.port,
        streamable_http_path=settings.mcp_path,
    )
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
    register_all_tools(
        mcp,
        build_tool_services(service_ctx, portfolio_enable_ai_summary=settings.portfolio_enable_ai_summary),
    )
    resolved_mode = resolve_transport_mode(settings.transport_mode)
    resolved_http_transport = resolve_http_transport(settings.http_transport)

    @mcp.custom_route(settings.health_path, methods=["GET"])
    async def health_check(_: object) -> Response:
        return JSONResponse({"status": "ok", "service": settings.app_name, "mode": resolved_mode})

    if not any(
        [
            finnhub_client,
            alpha_vantage_client,
            fmp_client,
            twelvedata_client,
            marketstack_client,
            fred_client,
            news_api_client,
            yahoo_client,
        ]
    ):
        print(
            "Warning: no external API providers configured. Set FINNHUB_API_KEY / ALPHAVANTAGE_API_KEY / "
            "FMP_API_KEY / TWELVEDATA_API_KEY / MARKETSTACK_API_KEY / FRED_API_KEY / NEWS_API_KEY."
        )
    if resolved_mode == "stdio":
        await mcp.run_stdio_async()
    elif resolved_http_transport == "streamable":
        await mcp.run_streamable_http_async()
    else:
        await mcp.run_sse_async()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()


