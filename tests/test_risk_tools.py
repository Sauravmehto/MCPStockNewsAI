from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.providers.models import NormalizedCandle
from mcp_server.services.base import ServiceContext, ServiceResult
from mcp_server.services.risk_service import RiskService
from mcp_server.services.stock_service import StockService
from mcp_server.utils.rate_limit import RateLimiterRegistry


class _StubStocks(StockService):
    def __init__(self) -> None:
        super().__init__(ServiceContext(providers={}, cache=TTLCache(), rate_limiter=RateLimiterRegistry(0.0)))

    def get_history(self, symbol: str, interval: str, from_unix: int, to_unix: int):
        candles = [
            NormalizedCandle(timestamp=1700000000 + i * 86400, open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000)
            for i in range(40)
        ]
        return ServiceResult(data=candles, source="stub")


def test_risk_sharpe_sortino() -> None:
    service = RiskService(_StubStocks())
    result = service.get_sharpe_sortino("AAPL", "D", 1, 2)
    assert result.data is not None
    assert "sharpe" in result.data
    assert "sortino" in result.data


