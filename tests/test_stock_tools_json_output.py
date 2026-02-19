import asyncio
import json
from types import SimpleNamespace

from mcp.server.fastmcp import FastMCP

from mcp_server.providers.models import NormalizedQuote
from mcp_server.services.base import ErrorEnvelope, ServiceResult
from mcp_server.tools.stocks_tools import register_stocks_tools


class _MockStockService:
    def __init__(self, quote_result: ServiceResult[NormalizedQuote]) -> None:
        self._quote_result = quote_result

    def get_quote(self, symbol: str) -> ServiceResult[NormalizedQuote]:
        return self._quote_result

    def get_profile(self, symbol: str):
        return ServiceResult(data=None)

    def get_history(self, symbol: str, interval: str, from_unix: int, to_unix: int):
        return ServiceResult(data=None)

    def get_news(self, symbol: str, from_date: str, to_date: str, limit: int = 10):
        return ServiceResult(data=None)

    def get_dividends(self, symbol: str, limit: int = 12):
        return ServiceResult(data=None)

    def get_splits(self, symbol: str, limit: int = 10):
        return ServiceResult(data=None)

    def get_earnings_calendar(self, symbol: str, limit: int = 8):
        return ServiceResult(data=None)


def _call_tool_result_string(mcp: FastMCP, name: str, arguments: dict[str, object]) -> str:
    _, metadata = asyncio.run(mcp.call_tool(name, arguments))
    return str(metadata.get("result") or "")


def test_stock_tool_success_is_json_with_source_and_data() -> None:
    quote = NormalizedQuote(
        symbol="AAPL",
        price=200.0,
        change=1.2,
        percent_change=0.6,
        high=202.0,
        low=198.0,
        open=199.5,
        previous_close=198.8,
        timestamp=1700000000,
        source="alphavantage",
    )
    service = _MockStockService(ServiceResult(data=quote, source="Alpha Vantage"))
    mcp = FastMCP(name="stock-tools-json-success")
    register_stocks_tools(mcp, SimpleNamespace(stocks=service))

    payload = _call_tool_result_string(mcp, "get_stock_price", {"symbol": "AAPL"})
    parsed = json.loads(payload)
    assert parsed["source"] == "Alpha Vantage"
    assert parsed["data"]["symbol"] == "AAPL"
    assert isinstance(parsed["data"]["price"], float)


def test_stock_tool_error_is_generic_json_without_raw_provider_details() -> None:
    service = _MockStockService(
        ServiceResult(
            data=None,
            error=ErrorEnvelope(
                code="UPSTREAM",
                message="upstream said token invalid: abc123",
                retriable=True,
                provider="finnhub",
            ),
        )
    )
    mcp = FastMCP(name="stock-tools-json-error")
    register_stocks_tools(mcp, SimpleNamespace(stocks=service))

    payload = _call_tool_result_string(mcp, "get_stock_price", {"symbol": "AAPL"})
    parsed = json.loads(payload)
    assert parsed == {"error": "All stock data providers are currently unavailable. Please try again later."}
    assert "abc123" not in payload


