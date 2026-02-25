"""Backward-compatible shim for older import path."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.services.base import ServiceContext
from mcp_server.tools.registry import build_tool_services, register_all_tools
from mcp_server.utils.rate_limit import RateLimiterRegistry


def register_stock_tools(
    mcp: FastMCP,
    finnhub_client=None,
    alpha_vantage_client=None,
    yahoo_client=None,
    fmp_client=None,
    fred_client=None,
    news_api_client=None,
    sec_client=None,
    cache_ttl_seconds: int = 60,
    provider_min_interval_seconds: float = 0.2,
) -> None:
    providers = {
        "finnhub": finnhub_client,
        "alphavantage": alpha_vantage_client,
        "yahoo": yahoo_client,
        "fmp": fmp_client,
        "fred": fred_client,
        "newsapi": news_api_client,
        "sec": sec_client,
    }
    ctx = ServiceContext(
        providers=providers,
        cache=TTLCache(default_ttl_seconds=cache_ttl_seconds),
        rate_limiter=RateLimiterRegistry(min_interval_seconds=provider_min_interval_seconds),
        cache_ttl_seconds=cache_ttl_seconds,
    )
    register_all_tools(mcp, build_tool_services(ctx))


