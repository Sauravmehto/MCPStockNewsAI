"""Application entrypoint for Local Stock Analyst MCP server."""

from __future__ import annotations

import asyncio
import gzip
import io
import os
import time

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
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
from mcp_server.protocol.compliance import configure_protocol_compliance
from mcp_server.prompts.market_prompts import register_market_prompts
from mcp_server.prompts.portfolio_prompts import register_portfolio_prompts
from mcp_server.resources.market_resources import register_market_resources
from mcp_server.resources.portfolio_resources import register_portfolio_resources
from mcp_server.runtime.limits import RateLimitExceeded, RequestLimiter
from mcp_server.runtime.monitoring import ServerMetrics, log_tool_event
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
    server_metrics = ServerMetrics()
    request_limiter = RequestLimiter(
        requests_per_minute=settings.default_requests_per_minute,
        queue_limit=settings.request_queue_limit,
    )
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
        request_limiter=request_limiter,
        server_metrics=server_metrics,
    )
    services = build_tool_services(
        service_ctx,
        portfolio_enable_ai_summary=settings.portfolio_enable_ai_summary,
        portfolio_resource_updated_callback=protocol.notify_resource_updated_sync,
    )
    register_all_tools(mcp, services)
    register_market_prompts(mcp)
    register_portfolio_prompts(mcp)
    register_market_resources(mcp, services, protocol)
    register_portfolio_resources(mcp, services)
    resolved_mode = resolve_transport_mode(settings.transport_mode)
    resolved_http_transport = resolve_http_transport(settings.http_transport)

    @mcp.custom_route(settings.health_path, methods=["GET"])
    async def health_check(_: object) -> Response:
        prompts = await mcp.list_prompts()
        resources = await mcp.list_resources()
        templates = await mcp.list_resource_templates()
        return JSONResponse(
            {
                "status": "ok",
                "service": settings.app_name,
                "mode": resolved_mode,
                "prompt_count": len(prompts),
                "resource_count": len(resources),
                "resource_template_count": len(templates),
            }
        )

    @mcp.custom_route("/mcp-capabilities", methods=["GET"])
    async def mcp_capabilities(_: object) -> Response:
        options = mcp._mcp_server.create_initialization_options()
        capabilities = options.capabilities.model_dump(by_alias=True, exclude_none=True)
        return JSONResponse(
            {
                "server_name": options.server_name,
                "server_version": options.server_version,
                "capabilities": capabilities,
            }
        )

    @mcp.custom_route("/tools/{tool_name}", methods=["POST"])
    async def guarded_tool_call(request: Request) -> Response:
        tool_name = request.path_params.get("tool_name", "unknown")
        started = time.perf_counter()
        body = await request.json()
        arguments = body.get("arguments") if isinstance(body, dict) else {}
        if not isinstance(arguments, dict):
            arguments = {}
        symbol = str(arguments.get("symbol") or "")
        client_id = str(request.headers.get("x-api-key") or request.headers.get("x-client-id") or request.client or "anonymous")
        try:
            request_limiter.acquire(client_id)
        except RateLimitExceeded as error:
            server_metrics.record_rate_limit_hit(client_id)
            return JSONResponse(
                {"error": True, "code": "RATE_LIMITED", "message": "Rate limit exceeded.", "timestamp": int(time.time())},
                status_code=429,
                headers={"Retry-After": str(max(1, int(error.retry_after_seconds)))},
            )
        try:
            content_blocks, metadata = await mcp.call_tool(tool_name, arguments)
            result_text = str(metadata.get("result") or "")
            compressed = io.BytesIO()
            with gzip.GzipFile(fileobj=compressed, mode="wb") as gz:
                gz.write(result_text.encode("utf-8"))
            latency_ms = (time.perf_counter() - started) * 1000.0
            warning = "slow_response" if latency_ms > 2000 else None
            log_tool_event(tool=tool_name, symbol=symbol or None, latency_ms=latency_ms, success=True, client_id=client_id, warning=warning)
            server_metrics.record(latency_ms=latency_ms, success=True)
            return Response(
                content=compressed.getvalue(),
                media_type="application/json",
                headers={"Content-Encoding": "gzip"},
            )
        except Exception:
            latency_ms = (time.perf_counter() - started) * 1000.0
            log_tool_event(tool=tool_name, symbol=symbol or None, latency_ms=latency_ms, success=False, client_id=client_id)
            server_metrics.record(latency_ms=latency_ms, success=False)
            return JSONResponse(
                {"error": True, "code": "DATA_UNAVAILABLE", "message": "Request failed.", "timestamp": int(time.time())},
                status_code=500,
            )
        finally:
            request_limiter.release()

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


