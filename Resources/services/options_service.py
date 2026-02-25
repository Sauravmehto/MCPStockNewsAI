"""Options-data service."""

from __future__ import annotations

from mcp_server.providers.models import NormalizedOptionsContract
from mcp_server.providers.yahoo_finance import YahooFinanceClient
from mcp_server.services.base import ServiceContext, ServiceResult, execute_with_fallback


class OptionsService:
    def __init__(self, ctx: ServiceContext) -> None:
        self.ctx = ctx

    def _yahoo(self) -> YahooFinanceClient | None:
        c = self.ctx.get_provider("yahoo")
        return c if isinstance(c, YahooFinanceClient) else None

    def get_chain(self, symbol: str) -> ServiceResult[list[NormalizedOptionsContract]]:
        return execute_with_fallback(
            "get_options_chain",
            [("Yahoo Finance", lambda: self._yahoo().get_options_chain(symbol) if self._yahoo() else None)],
            self.ctx,
        )

    def get_iv_summary(self, symbol: str) -> ServiceResult[dict[str, float]]:
        chain = self.get_chain(symbol)
        if not chain.data:
            return ServiceResult(data=None, source=chain.source, warning=chain.warning, error=chain.error)
        ivs = [c.implied_volatility for c in chain.data if c.implied_volatility is not None]
        if not ivs:
            return ServiceResult(
                data=None,
                source=chain.source,
                warning=chain.warning,
                error=None,
            )
        return ServiceResult(
            data={"avg_iv": sum(ivs) / len(ivs), "max_iv": max(ivs), "min_iv": min(ivs)},
            source=chain.source,
            warning=chain.warning,
        )

    def get_greeks_summary(self, symbol: str) -> ServiceResult[dict[str, float]]:
        chain = self.get_chain(symbol)
        if not chain.data:
            return ServiceResult(data=None, source=chain.source, warning=chain.warning, error=chain.error)
        def _avg(values: list[float | None]) -> float:
            clean = [v for v in values if v is not None]
            return sum(clean) / len(clean) if clean else 0.0
        return ServiceResult(
            data={
                "delta": _avg([c.delta for c in chain.data]),
                "gamma": _avg([c.gamma for c in chain.data]),
                "theta": _avg([c.theta for c in chain.data]),
                "vega": _avg([c.vega for c in chain.data]),
            },
            source=chain.source,
            warning=chain.warning,
        )

    def get_unusual_activity(self, symbol: str) -> ServiceResult[list[str]]:
        chain = self.get_chain(symbol)
        if not chain.data:
            return ServiceResult(data=None, source=chain.source, warning=chain.warning, error=chain.error)
        flagged = sorted(
            [
                c
                for c in chain.data
                if (c.volume or 0) > 0 and (c.open_interest or 0) > 0 and (c.volume or 0) > (c.open_interest or 0) * 1.5
            ],
            key=lambda x: x.volume or 0,
            reverse=True,
        )[:10]
        lines = [f"{c.call_put.upper()} {c.strike:.2f} exp {c.expiration} vol {c.volume} oi {c.open_interest}" for c in flagged]
        return ServiceResult(data=lines, source=chain.source, warning=chain.warning)

    def get_max_pain(self, symbol: str) -> ServiceResult[dict[str, float]]:
        chain = self.get_chain(symbol)
        if not chain.data:
            return ServiceResult(data=None, source=chain.source, warning=chain.warning, error=chain.error)
        strikes = sorted({c.strike for c in chain.data})
        if not strikes:
            return ServiceResult(data=None, source=chain.source, warning=chain.warning, error=chain.error)
        pain: list[tuple[float, float]] = []
        calls = [c for c in chain.data if c.call_put == "call"]
        puts = [c for c in chain.data if c.call_put == "put"]
        for settle in strikes:
            total = 0.0
            for c in calls:
                total += max(0.0, settle - c.strike) * float(c.open_interest or 0)
            for p in puts:
                total += max(0.0, p.strike - settle) * float(p.open_interest or 0)
            pain.append((settle, total))
        min_settle, min_val = min(pain, key=lambda item: item[1])
        return ServiceResult(data={"max_pain_strike": min_settle, "aggregate_pain": min_val}, source=chain.source, warning=chain.warning)


