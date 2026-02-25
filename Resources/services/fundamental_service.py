"""Fundamental-data service."""

from __future__ import annotations

from mcp_server.providers.alpha_vantage import AlphaVantageClient
from mcp_server.providers.finnhub import FinnhubClient
from mcp_server.providers.fmp import FmpClient
from mcp_server.providers.models import NormalizedKeyFinancials, NormalizedSecFiling, NormalizedStatement
from mcp_server.providers.sec_edgar import SecEdgarClient
from mcp_server.services.base import ServiceContext, ServiceResult, execute_with_fallback


class FundamentalService:
    def __init__(self, ctx: ServiceContext) -> None:
        self.ctx = ctx

    def _finnhub(self) -> FinnhubClient | None:
        c = self.ctx.get_provider("finnhub")
        return c if isinstance(c, FinnhubClient) else None

    def _alpha(self) -> AlphaVantageClient | None:
        c = self.ctx.get_provider("alphavantage")
        return c if isinstance(c, AlphaVantageClient) else None

    def _fmp(self) -> FmpClient | None:
        c = self.ctx.get_provider("fmp")
        return c if isinstance(c, FmpClient) else None

    def _sec(self) -> SecEdgarClient | None:
        c = self.ctx.get_provider("sec")
        return c if isinstance(c, SecEdgarClient) else None

    def get_metrics(self, symbol: str) -> ServiceResult[NormalizedKeyFinancials]:
        return execute_with_fallback(
            "get_key_financials",
            [
                ("Finnhub", lambda: self._finnhub().get_key_financials(symbol) if self._finnhub() else None),
                ("FMP", lambda: self._fmp().get_key_metrics(symbol) if self._fmp() else None),
                ("Alpha Vantage", lambda: self._alpha().get_key_financials(symbol) if self._alpha() else None),
            ],
            self.ctx,
        )

    def get_statement(self, symbol: str, statement_type: str, period: str = "annual") -> ServiceResult[list[NormalizedStatement]]:
        return execute_with_fallback(
            f"get_{statement_type}_statement",
            [("FMP", lambda: self._fmp().get_statement(symbol, statement_type, period) if self._fmp() else None)],
            self.ctx,
        )

    def get_sec_filings(self, symbol: str, limit: int = 10) -> ServiceResult[list[NormalizedSecFiling]]:
        return execute_with_fallback(
            "get_sec_filings",
            [("SEC", lambda: self._sec().get_recent_filings(symbol, limit) if self._sec() else None)],
            self.ctx,
        )

    def get_ratings(self, symbol: str) -> ServiceResult[dict[str, str]]:
        metrics = self.get_metrics(symbol)
        if not metrics.data:
            return ServiceResult(data=None, source=metrics.source, warning=metrics.warning, error=metrics.error)
        pe = metrics.data.pe_ratio
        style = "value" if pe is not None and pe < 20 else "growth" if pe is not None and pe >= 20 else "unknown"
        return ServiceResult(data={"style": style, "rating": "neutral"}, source=metrics.source, warning=metrics.warning)

    def get_targets(self, symbol: str) -> ServiceResult[dict[str, float | None]]:
        metrics = self.get_metrics(symbol)
        if not metrics.data:
            return ServiceResult(data=None, source=metrics.source, warning=metrics.warning, error=metrics.error)
        eps = metrics.data.eps
        pe = metrics.data.pe_ratio
        target = eps * pe if eps is not None and pe is not None else None
        return ServiceResult(data={"implied_price_target": target}, source=metrics.source, warning=metrics.warning)

    def get_ownership_snapshot(self, symbol: str) -> ServiceResult[dict[str, str]]:
        filings = self.get_sec_filings(symbol, limit=20)
        if not filings.data:
            return ServiceResult(data=None, source=filings.source, warning=filings.warning, error=filings.error)
        insider_forms = [item for item in filings.data if item.form in {"3", "4", "5"}]
        institutional_forms = [item for item in filings.data if item.form in {"13F-HR", "SC 13D", "SC 13G"}]
        return ServiceResult(
            data={
                "insider_activity_signal": f"{len(insider_forms)} insider filing(s) in recent window",
                "institutional_activity_signal": f"{len(institutional_forms)} ownership filing(s) in recent window",
            },
            source=filings.source,
            warning=filings.warning,
        )


