from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.services.base import ServiceContext
from mcp_server.services.market_service import MarketService
from mcp_server.services.stock_service import StockService
from mcp_server.utils.rate_limit import RateLimiterRegistry


def test_market_status_returns_payload() -> None:
    stocks = StockService(ServiceContext(providers={}, cache=TTLCache(), rate_limiter=RateLimiterRegistry(0.0)))
    market = MarketService(ServiceContext(providers={}, cache=TTLCache(), rate_limiter=RateLimiterRegistry(0.0)), stocks)
    result = market.get_market_status()
    assert result.data is not None
    assert "status" in result.data


