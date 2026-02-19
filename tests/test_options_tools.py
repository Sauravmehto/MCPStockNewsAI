import pytest

from mcp_server.cache.ttl_cache import TTLCache
from mcp_server.providers.models import NormalizedOptionsContract
from mcp_server.providers.yahoo_finance import YahooFinanceClient
from mcp_server.services.base import ServiceContext
from mcp_server.services.options_service import OptionsService
from mcp_server.utils.rate_limit import RateLimiterRegistry


def test_options_iv_summary(monkeypatch) -> None:
    yahoo = YahooFinanceClient()
    monkeypatch.setattr(
        yahoo,
        "get_options_chain",
        lambda symbol: [
            NormalizedOptionsContract(symbol=symbol, expiration="1", strike=100, call_put="call", implied_volatility=0.2),
            NormalizedOptionsContract(symbol=symbol, expiration="1", strike=105, call_put="put", implied_volatility=0.4),
        ],
    )
    service = OptionsService(
        ServiceContext(providers={"yahoo": yahoo}, cache=TTLCache(), rate_limiter=RateLimiterRegistry(0.0))
    )
    result = service.get_iv_summary("AAPL")
    assert result.data is not None
    assert result.data["avg_iv"] == pytest.approx(0.3)


