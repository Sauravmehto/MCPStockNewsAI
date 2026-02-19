from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.providers.alpha_vantage import AlphaVantageClient
from mcp_server.providers.finnhub import FinnhubClient
from mcp_server.providers.fmp import FmpClient
from mcp_server.providers.http import ProviderError
from mcp_server.providers.marketstack import MarketStackClient
from mcp_server.providers.models import NormalizedQuote
from mcp_server.services.base import ServiceContext
from mcp_server.services.fallback_manager import FallbackManager, ProviderAttempt
from mcp_server.services.provider_status import ProviderStatus
from mcp_server.services.stock_service import StockService
from mcp_server.utils.rate_limit import RateLimiterRegistry
from mcp_server.providers.twelve_data import TwelveDataClient
from mcp_server.providers.web_quote_search import WebQuoteSearchClient


def _ctx() -> ServiceContext:
    return ServiceContext(providers={}, cache=TTLCache(), rate_limiter=RateLimiterRegistry(0.0))


def test_fallback_manager_disables_rate_limited_provider_and_skips_while_disabled() -> None:
    status = ProviderStatus()
    manager = FallbackManager(
        ctx=_ctx(),
        provider_status=status,
        rate_limit_disable_seconds={"alphavantage": 60},
    )
    calls = {"alpha": 0, "finnhub": 0}

    def alpha_call():
        calls["alpha"] += 1
        raise ProviderError("alphavantage", "RATE_LIMIT", "requests per day exceeded", 429)

    def finnhub_call():
        calls["finnhub"] += 1
        return NormalizedQuote(
            symbol="AAPL",
            price=123.0,
            change=1.0,
            percent_change=0.8,
            high=124.0,
            low=122.0,
            open=122.5,
            previous_close=122.0,
            timestamp=1700000000,
            source="finnhub",
        )

    first = manager.execute(
        operation="get_quote",
        symbol="AAPL",
        attempts=[
            ProviderAttempt("alphavantage", "Alpha Vantage", alpha_call),
            ProviderAttempt("finnhub", "Finnhub", finnhub_call),
        ],
    )
    assert first.data is not None
    assert first.source == "Finnhub"
    assert status.is_disabled("alphavantage") is True
    assert calls["alpha"] == 1
    assert calls["finnhub"] == 1

    second = manager.execute(
        operation="get_quote",
        symbol="AAPL",
        attempts=[
            ProviderAttempt("alphavantage", "Alpha Vantage", alpha_call),
            ProviderAttempt("finnhub", "Finnhub", finnhub_call),
        ],
    )
    assert second.data is not None
    assert second.source == "Finnhub"
    assert calls["alpha"] == 1  # disabled provider is skipped; no extra call
    assert calls["finnhub"] == 2


def test_fallback_manager_returns_generic_error_without_upstream_leakage() -> None:
    manager = FallbackManager(ctx=_ctx(), provider_status=ProviderStatus())

    def failing_call():
        raise ProviderError("finnhub", "UPSTREAM", "sensitive upstream payload: api_key=secret")

    result = manager.execute(
        operation="get_quote",
        symbol="AAPL",
        attempts=[ProviderAttempt("finnhub", "Finnhub", failing_call)],
    )
    assert result.data is None
    assert result.error is not None
    assert result.error.message == "All stock data providers are currently unavailable. Please try again later."
    assert "secret" not in result.error.message


def test_stock_service_uses_web_search_quote_when_api_providers_fail(monkeypatch) -> None:
    alpha = AlphaVantageClient("x")
    finnhub = FinnhubClient("x")
    fmp = FmpClient("x")
    twelvedata = TwelveDataClient("x")
    marketstack = MarketStackClient("x")
    web = WebQuoteSearchClient()

    for provider in (alpha, finnhub, fmp, twelvedata, marketstack):
        monkeypatch.setattr(
            provider,
            "get_quote",
            lambda symbol: (_ for _ in ()).throw(ProviderError("alphavantage", "UPSTREAM", "provider failed")),
        )

    monkeypatch.setattr(
        web,
        "get_quote",
        lambda symbol: NormalizedQuote(
            symbol=symbol,
            price=99.0,
            change=0.5,
            percent_change=0.4,
            high=100.0,
            low=98.0,
            open=98.8,
            previous_close=98.5,
            timestamp=1700000000,
            source="websearch",
        ),
    )

    service = StockService(
        ServiceContext(
            providers={
                "alphavantage": alpha,
                "finnhub": finnhub,
                "fmp": fmp,
                "twelvedata": twelvedata,
                "marketstack": marketstack,
                "websearch": web,
            },
            cache=TTLCache(),
            rate_limiter=RateLimiterRegistry(0.0),
        )
    )
    result = service.get_quote("AAPL")
    assert result.data is not None
    assert result.source == "Web Search"


