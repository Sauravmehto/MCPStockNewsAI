from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.providers.alpha_vantage import AlphaVantageClient
from mcp_server.providers.finnhub import FinnhubClient
from mcp_server.providers.models import NormalizedQuote
from mcp_server.services.base import ServiceContext
from mcp_server.services.stock_service import StockService
from mcp_server.utils.rate_limit import RateLimiterRegistry


def test_stock_service_fallback_to_alpha(monkeypatch) -> None:
    finnhub = FinnhubClient("x")
    alpha = AlphaVantageClient("y")

    monkeypatch.setattr(finnhub, "get_quote", lambda symbol: None)
    monkeypatch.setattr(
        alpha,
        "get_quote",
        lambda symbol: NormalizedQuote(
            symbol=symbol,
            price=100.0,
            change=1.0,
            percent_change=1.0,
            high=101.0,
            low=99.0,
            open=99.5,
            previous_close=99.0,
            timestamp=1700000000,
            source="alphavantage",
        ),
    )

    service = StockService(
        ServiceContext(
            providers={"finnhub": finnhub, "alphavantage": alpha},
            cache=TTLCache(),
            rate_limiter=RateLimiterRegistry(0.0),
        )
    )
    result = service.get_quote("AAPL")
    assert result.data is not None
    assert result.source == "Alpha Vantage"


