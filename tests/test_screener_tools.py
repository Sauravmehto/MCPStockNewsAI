from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.providers.models import NormalizedCompanyProfile, NormalizedQuote
from mcp_server.services.base import ServiceContext, ServiceResult
from mcp_server.services.screener_service import ScreenerService
from mcp_server.services.stock_service import StockService
from mcp_server.utils.rate_limit import RateLimiterRegistry


class _StubStocks(StockService):
    def __init__(self) -> None:
        super().__init__(ServiceContext(providers={}, cache=TTLCache(), rate_limiter=RateLimiterRegistry(0.0)))

    def get_quote(self, symbol: str):
        return ServiceResult(
            data=NormalizedQuote(
                symbol=symbol,
                price=120.0,
                change=0.0,
                percent_change=0.0,
                high=121.0,
                low=119.0,
                open=119.0,
                previous_close=119.5,
                timestamp=1700000000,
                source="finnhub",
            ),
            source="stub",
        )

    def get_profile(self, symbol: str):
        return ServiceResult(data=NormalizedCompanyProfile(symbol=symbol, industry="Technology"), source="stub")


def test_screener_returns_filtered_symbols() -> None:
    service = ScreenerService(_StubStocks())
    result = service.screen(["AAPL", "MSFT"], min_price=100, max_price=130, sector_hint="tech")
    assert result.data is not None
    assert len(result.data) == 2


