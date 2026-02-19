from types import SimpleNamespace

from mcp.server.fastmcp import FastMCP

from mcp_server.tools.portfolio_tools import register_portfolio_tools


class _MockPortfolioService:
    def validate_excel(self, file_path: str):
        return {"ok": True, "file_path": file_path}

    def analyze_excel(self, file_path: str, include_ai_summary: bool = True):
        return {"ok": True, "file_path": file_path, "include_ai_summary": include_ai_summary}

    def benchmark_report(self, file_path: str):
        return {"ok": True, "report": "benchmark", "file_path": file_path}

    def stress_test(self, file_path: str):
        return {"ok": True, "report": "stress", "file_path": file_path}


def test_register_portfolio_tools() -> None:
    mcp = FastMCP(name="test-portfolio-tools")
    services = SimpleNamespace(portfolio=_MockPortfolioService())
    register_portfolio_tools(mcp, services)
    assert mcp is not None


