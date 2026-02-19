from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.providers.fmp import FmpClient
from mcp_server.providers.models import NormalizedKeyFinancials
from mcp_server.services.base import ServiceContext
from mcp_server.services.fundamental_service import FundamentalService
from mcp_server.utils.rate_limit import RateLimiterRegistry


def test_fundamental_metrics_from_fmp(monkeypatch) -> None:
    fmp = FmpClient("dummy")
    monkeypatch.setattr(
        fmp,
        "get_key_metrics",
        lambda symbol: NormalizedKeyFinancials(symbol=symbol, pe_ratio=22.0, eps=4.0, source="fmp"),
    )
    service = FundamentalService(
        ServiceContext(providers={"fmp": fmp}, cache=TTLCache(), rate_limiter=RateLimiterRegistry(0.0))
    )
    result = service.get_metrics("MSFT")
    assert result.data is not None
    assert result.data.pe_ratio == 22.0


