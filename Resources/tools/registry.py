"""Domain tool registry entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from mcp_server.portfolio.portfolio_service import PortfolioService
from mcp_server.services.fundamental_service import FundamentalService
from mcp_server.services.market_service import MarketService
from mcp_server.services.news_service import NewsService
from mcp_server.services.options_service import OptionsService
from mcp_server.services.risk_service import RiskService
from mcp_server.services.screener_service import ScreenerService
from mcp_server.services.stock_service import StockService
from mcp_server.services.technical_service import TechnicalService
from mcp_server.tools.fundamental_tools import register_fundamental_tools
from mcp_server.tools.market_tools import register_market_tools
from mcp_server.tools.news_tools import register_news_tools
from mcp_server.tools.options_tools import register_options_tools
from mcp_server.tools.portfolio_tools import register_portfolio_tools
from mcp_server.tools.risk_tools import register_risk_tools
from mcp_server.tools.screener_tools import register_screener_tools
from mcp_server.tools.stocks_tools import register_stocks_tools
from mcp_server.tools.technical_tools import register_technical_tools


@dataclass
class ToolServices:
    market: MarketService
    stocks: StockService
    technical: TechnicalService
    fundamental: FundamentalService
    options: OptionsService
    risk: RiskService
    news: NewsService
    screener: ScreenerService
    portfolio: PortfolioService


def build_tool_services(ctx, portfolio_enable_ai_summary: bool = True) -> ToolServices:
    stocks = StockService(ctx)
    return ToolServices(
        market=MarketService(ctx, stocks),
        stocks=stocks,
        technical=TechnicalService(stocks),
        fundamental=FundamentalService(ctx),
        options=OptionsService(ctx),
        risk=RiskService(stocks),
        news=NewsService(ctx),
        screener=ScreenerService(stocks),
        portfolio=PortfolioService(ctx, enable_ai_summary=portfolio_enable_ai_summary),
    )


def register_all_tools(mcp: FastMCP, services: ToolServices) -> None:
    register_market_tools(mcp, services)
    register_stocks_tools(mcp, services)
    register_technical_tools(mcp, services)
    register_fundamental_tools(mcp, services)
    register_options_tools(mcp, services)
    register_risk_tools(mcp, services)
    register_news_tools(mcp, services)
    register_screener_tools(mcp, services)
    register_portfolio_tools(mcp, services)


