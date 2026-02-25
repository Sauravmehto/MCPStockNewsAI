"""Environment-driven settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    """Runtime settings for local/stdin and HTTP-hosted modes."""

    app_name: str = "local-stock-analyst"
    app_version: str = "1.0.0"
    transport_mode: str = "auto"
    http_transport: str = "sse"
    host: str = "0.0.0.0"
    port: int = 8000
    mcp_path: str = "/mcp"
    health_path: str = "/health"
    finnhub_api_key: str | None = None
    alphavantage_api_key: str | None = None
    yahoo_finance_enabled: bool = True
    fmp_api_key: str | None = None
    twelvedata_api_key: str | None = None
    marketstack_api_key: str | None = None
    fred_api_key: str | None = None
    news_api_key: str | None = None
    sec_user_agent: str = "local-stock-analyst/1.0 (support@example.com)"
    claude_api_key: str | None = None
    claude_model: str = "claude-sonnet-4-5-20250929"
    portfolio_enable_ai_summary: bool = True
    request_timeout_seconds: float = 15.0
    cache_ttl_seconds: int = 60
    provider_min_interval_seconds: float = 0.2
    default_requests_per_minute: int = 100
    request_queue_limit: int = 200
    cache_ttl_quote_seconds: int = 15
    cache_ttl_candles_seconds: int = 60
    cache_ttl_news_seconds: int = 300
    cache_ttl_fundamentals_seconds: int = 3600


def _as_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    """Load runtime settings from environment variables."""
    load_dotenv()

    return Settings(
        transport_mode=os.getenv("TRANSPORT_MODE", "auto").strip().lower(),
        http_transport=os.getenv("HTTP_TRANSPORT", "sse").strip().lower(),
        host=os.getenv("HOST", "0.0.0.0"),
        port=_as_int(os.getenv("PORT"), 8000),
        mcp_path=os.getenv("MCP_PATH", "/mcp"),
        health_path=os.getenv("HEALTH_PATH", "/health"),
        finnhub_api_key=os.getenv("FINNHUB_API_KEY"),
        alphavantage_api_key=os.getenv("ALPHAVANTAGE_API_KEY"),
        yahoo_finance_enabled=_as_bool(os.getenv("YAHOO_FINANCE_ENABLED"), True),
        fmp_api_key=os.getenv("FMP_API_KEY"),
        twelvedata_api_key=os.getenv("TWELVEDATA_API_KEY"),
        marketstack_api_key=os.getenv("MARKETSTACK_API_KEY"),
        fred_api_key=os.getenv("FRED_API_KEY"),
        news_api_key=os.getenv("NEWS_API_KEY"),
        sec_user_agent=os.getenv(
            "SEC_USER_AGENT",
            "local-stock-analyst/1.0 (support@example.com)",
        ),
        claude_api_key=os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
        claude_model=(
            os.getenv("CLAUDE_MODEL")
            or os.getenv("ANTHROPIC_MODEL")
            or "claude-sonnet-4-5-20250929"
        ),
        portfolio_enable_ai_summary=_as_bool(os.getenv("PORTFOLIO_ENABLE_AI_SUMMARY"), True),
        request_timeout_seconds=_as_float(os.getenv("REQUEST_TIMEOUT_SECONDS"), 15.0),
        cache_ttl_seconds=_as_int(os.getenv("CACHE_TTL_SECONDS"), 60),
        provider_min_interval_seconds=_as_float(os.getenv("PROVIDER_MIN_INTERVAL_SECONDS"), 0.2),
        default_requests_per_minute=_as_int(os.getenv("DEFAULT_REQUESTS_PER_MINUTE"), 100),
        request_queue_limit=_as_int(os.getenv("REQUEST_QUEUE_LIMIT"), 200),
        cache_ttl_quote_seconds=_as_int(os.getenv("CACHE_TTL_QUOTE_SECONDS"), 15),
        cache_ttl_candles_seconds=_as_int(os.getenv("CACHE_TTL_CANDLES_SECONDS"), 60),
        cache_ttl_news_seconds=_as_int(os.getenv("CACHE_TTL_NEWS_SECONDS"), 300),
        cache_ttl_fundamentals_seconds=_as_int(os.getenv("CACHE_TTL_FUNDAMENTALS_SECONDS"), 3600),
    )


