"""Portfolio news impact tool registration."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from mcp_server.providers.anthropic_client import AnthropicClient
from mcp_server.scoring.news_impact_engine import (
    infer_sector,
    rank_symbol_impacts,
    score_news_impact,
    score_symbol_news_impact,
)
from mcp_server.services.base import validate_symbol
from mcp_server.tools.common import ensure_data

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def _cache_file_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    cache_dir = root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "portfolio_news_impact_latest.json"


def _write_latest_cache(payload: dict[str, object]) -> str:
    target = _cache_file_path()
    target.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return str(target)


def register_portfolio_news_impact_tools(mcp: FastMCP, services: ToolServices) -> None:
    @mcp.tool(description="Score portfolio holdings by potential downside risk from curated and live news.")
    def get_portfolio_news_impact(
        symbols: list[str],
        news_items: list[str],
        include_live_news: bool = True,
    ) -> str:
        normalized_symbols = [validate_symbol(symbol) for symbol in symbols]
        if not normalized_symbols:
            raise ValueError("At least one symbol is required.")

        anthropic_client_raw = services.news.ctx.get_provider("anthropic")
        anthropic_client = anthropic_client_raw if isinstance(anthropic_client_raw, AnthropicClient) else None

        market_items: list[str] = []
        if include_live_news:
            market_result = services.news.get_market_headlines(limit=10)
            market_items = [str(item).strip() for item in (market_result.data or []) if str(item).strip()]

        rows: list[dict[str, object]] = []
        for symbol in normalized_symbols:
            quantity = 1.0  # Baseline per-share estimate when portfolio quantities are not provided.

            quote_result = services.stocks.get_quote(symbol)
            quote = ensure_data(quote_result.data, quote_result.error, default_message=f"Quote unavailable for {symbol}.")
            profile_result = services.stocks.get_profile(symbol)
            profile = profile_result.data
            metrics_result = services.fundamental.get_metrics(symbol)
            metrics = metrics_result.data

            beta = 1.0
            if metrics and metrics.beta is not None:
                beta = float(metrics.beta)
            sector = infer_sector(symbol=symbol, profile_industry=(profile.industry if profile else None))

            company_items: list[str] = []
            if include_live_news:
                company_result = services.news.get_company_news(symbol, limit=10)
                company_items = [item.headline.strip() for item in (company_result.data or []) if item.headline and item.headline.strip()]

            requested_items = [item.strip() for item in news_items if item and item.strip()]
            symbol_news = requested_items + company_items + market_items
            row = score_symbol_news_impact(
                symbol=symbol,
                quantity=quantity,
                price=float(quote.price),
                beta=beta,
                sector=sector,
                news_items=symbol_news,
                anthropic_client=anthropic_client,
            )
            row["quote_source"] = quote_result.source
            row["profile_source"] = profile_result.source
            row["metrics_source"] = metrics_result.source
            row["profile"] = asdict(profile) if profile else None
            rows.append(row)

        ranked = rank_symbol_impacts(rows)
        payload = {
            "generated_at": int(time.time()),
            "include_live_news": include_live_news,
            "input_symbols": normalized_symbols,
            "impact_basis": "per_share",
            "ranked_positions": ranked,
        }
        cache_path = _write_latest_cache(payload)
        payload["cache_file"] = cache_path
        return json.dumps(payload, ensure_ascii=True)

    @mcp.tool(description="Score one symbol against curated plus optional live headlines and return item-level impact details.")
    def get_symbol_news_impact(
        symbol: str,
        news_items: list[str],
        include_live_news: bool = True,
    ) -> str:
        normalized_symbol = validate_symbol(symbol)

        anthropic_client_raw = services.news.ctx.get_provider("anthropic")
        anthropic_client = anthropic_client_raw if isinstance(anthropic_client_raw, AnthropicClient) else None

        quote_result = services.stocks.get_quote(normalized_symbol)
        quote = ensure_data(quote_result.data, quote_result.error, default_message=f"Quote unavailable for {normalized_symbol}.")
        profile_result = services.stocks.get_profile(normalized_symbol)
        profile = profile_result.data
        metrics_result = services.fundamental.get_metrics(normalized_symbol)
        metrics = metrics_result.data

        beta = float(metrics.beta) if metrics and metrics.beta is not None else 1.0
        sector = infer_sector(symbol=normalized_symbol, profile_industry=(profile.industry if profile else None))

        market_items: list[str] = []
        company_items: list[str] = []
        if include_live_news:
            market_result = services.news.get_market_headlines(limit=10)
            market_items = [str(item).strip() for item in (market_result.data or []) if str(item).strip()]
            company_result = services.news.get_company_news(normalized_symbol, limit=10)
            company_items = [item.headline.strip() for item in (company_result.data or []) if item.headline and item.headline.strip()]

        requested_items = [item.strip() for item in news_items if item and item.strip()]
        merged_items = (requested_items + company_items + market_items)[:40]
        if not merged_items:
            raise ValueError("At least one non-empty news item is required.")

        scored_items = [
            score_news_impact(
                symbol=normalized_symbol,
                news_item=item,
                price=float(quote.price),
                beta=beta,
                qty=1.0,
                anthropic_client=anthropic_client,
            )
            for item in merged_items
        ]
        summary = score_symbol_news_impact(
            symbol=normalized_symbol,
            quantity=1.0,
            price=float(quote.price),
            beta=beta,
            sector=sector,
            news_items=merged_items,
            anthropic_client=anthropic_client,
        )
        summary["items"] = scored_items
        payload = {
            "generated_at": int(time.time()),
            "symbol": normalized_symbol,
            "include_live_news": include_live_news,
            "news_count": len(merged_items),
            "summary": summary,
            "quote_source": quote_result.source,
            "profile_source": profile_result.source,
            "metrics_source": metrics_result.source,
        }
        return json.dumps(payload, ensure_ascii=True)

    @mcp.tool(description="Rank a symbol watchlist by estimated downside exposure using optional live news.")
    def get_watchlist_news_impact(
        symbols: list[str],
        include_live_news: bool = True,
    ) -> str:
        normalized_symbols = [validate_symbol(symbol) for symbol in symbols]
        if not normalized_symbols:
            raise ValueError("At least one symbol is required.")

        anthropic_client_raw = services.news.ctx.get_provider("anthropic")
        anthropic_client = anthropic_client_raw if isinstance(anthropic_client_raw, AnthropicClient) else None

        market_items: list[str] = []
        if include_live_news:
            market_result = services.news.get_market_headlines(limit=10)
            market_items = [str(item).strip() for item in (market_result.data or []) if str(item).strip()]

        rows: list[dict[str, object]] = []
        for symbol_item in normalized_symbols:
            quote_result = services.stocks.get_quote(symbol_item)
            quote = ensure_data(quote_result.data, quote_result.error, default_message=f"Quote unavailable for {symbol_item}.")
            profile_result = services.stocks.get_profile(symbol_item)
            profile = profile_result.data
            metrics_result = services.fundamental.get_metrics(symbol_item)
            metrics = metrics_result.data

            beta = float(metrics.beta) if metrics and metrics.beta is not None else 1.0
            sector = infer_sector(symbol=symbol_item, profile_industry=(profile.industry if profile else None))
            company_items: list[str] = []
            if include_live_news:
                company_result = services.news.get_company_news(symbol_item, limit=10)
                company_items = [item.headline.strip() for item in (company_result.data or []) if item.headline and item.headline.strip()]

            row = score_symbol_news_impact(
                symbol=symbol_item,
                quantity=1.0,
                price=float(quote.price),
                beta=beta,
                sector=sector,
                news_items=(company_items + market_items),
                anthropic_client=anthropic_client,
            )
            row["quote_source"] = quote_result.source
            row["profile_source"] = profile_result.source
            row["metrics_source"] = metrics_result.source
            rows.append(row)

        payload = {
            "generated_at": int(time.time()),
            "include_live_news": include_live_news,
            "input_symbols": normalized_symbols,
            "impact_basis": "per_share",
            "ranked_positions": rank_symbol_impacts(rows),
        }
        return json.dumps(payload, ensure_ascii=True)


