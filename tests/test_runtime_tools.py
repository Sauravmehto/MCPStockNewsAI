import asyncio
import json
from dataclasses import dataclass
from types import SimpleNamespace

from mcp.server.fastmcp import FastMCP

from mcp_server.tools.news_tools import register_news_tools
from mcp_server.tools.runtime_tools import register_runtime_tools


@dataclass
class _Health:
    status: str = "ok"


class _MockRuntimeService:
    def get_server_health(self) -> _Health:
        return _Health()


class _MockNewsService:
    def get_market_headlines(self, limit: int = 10):  # noqa: ANN001
        return SimpleNamespace(data=["headline"], source="unit-test", warning=None, error=None)

    def get_company_news(self, symbol_or_query: str, limit: int = 10):  # noqa: ANN001
        return SimpleNamespace(data=[], source="unit-test", warning=None, error=None)


def _call_tool_result_string(mcp: FastMCP, name: str, arguments: dict[str, object]) -> str:
    _, metadata = asyncio.run(mcp.call_tool(name, arguments))
    return str(metadata.get("result") or "")


def test_tool_search_finds_tools_and_schema() -> None:
    mcp = FastMCP(name="runtime-tools-search")
    services = SimpleNamespace(runtime=_MockRuntimeService(), news=_MockNewsService())
    register_news_tools(mcp, services)
    register_runtime_tools(mcp, services)

    payload_text = _call_tool_result_string(mcp, "tool_search", {"query": "market news", "limit": 10})
    payload = json.loads(payload_text)
    assert payload["count"] >= 1
    names = [row["name"] for row in payload["tools"]]
    assert "get_market_news" in names

