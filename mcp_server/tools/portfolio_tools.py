"""Portfolio-domain MCP tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_portfolio_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Validate portfolio Excel file format and constraints.")
    def validate_portfolio_excel(file_path: str) -> str:
        payload = services.portfolio.validate_excel(file_path)
        return json.dumps(payload, ensure_ascii=True)

    @mcp.tool(description="Analyze portfolio Excel and return advanced analytics JSON.")
    def analyze_portfolio_excel(file_path: str, include_ai_summary: bool = True) -> str:
        payload = services.portfolio.analyze_excel(file_path, include_ai_summary=include_ai_summary)
        return json.dumps(payload, ensure_ascii=True)

    @mcp.tool(description="Return benchmark-focused report versus SP500 from portfolio file.")
    def portfolio_benchmark_report(file_path: str) -> str:
        payload = services.portfolio.benchmark_report(file_path)
        return json.dumps(payload, ensure_ascii=True)

    @mcp.tool(description="Return portfolio stress test scenarios from portfolio file.")
    def portfolio_stress_test(file_path: str) -> str:
        payload = services.portfolio.stress_test(file_path)
        return json.dumps(payload, ensure_ascii=True)


