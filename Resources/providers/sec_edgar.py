"""SEC EDGAR adapter."""

from __future__ import annotations

from mcp_server.providers.http import fetch_json
from mcp_server.providers.models import NormalizedSecFiling


def _symbol_to_cik(symbol: str, user_agent: str, timeout_seconds: float) -> str | None:
    data = fetch_json(
        "https://www.sec.gov/files/company_tickers.json",
        provider="sec",
        timeout_seconds=timeout_seconds,
        headers={"User-Agent": user_agent},
    )
    if not isinstance(data, dict):
        return None
    needle = symbol.upper()
    for value in data.values():
        if not isinstance(value, dict):
            continue
        if str(value.get("ticker") or "").upper() == needle:
            cik = value.get("cik_str")
            if isinstance(cik, int):
                return str(cik).zfill(10)
            if isinstance(cik, str) and cik.strip():
                return cik.strip().zfill(10)
    return None


class SecEdgarClient:
    def __init__(self, user_agent: str, timeout_seconds: float = 15.0) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def get_recent_filings(self, symbol: str, limit: int = 10) -> list[NormalizedSecFiling] | None:
        cik = _symbol_to_cik(symbol, self.user_agent, self.timeout_seconds)
        if not cik:
            return None
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        data = fetch_json(
            url,
            provider="sec",
            timeout_seconds=self.timeout_seconds,
            headers={"User-Agent": self.user_agent},
        )
        recent = ((data or {}).get("filings") or {}).get("recent") if isinstance(data, dict) else None
        if not isinstance(recent, dict):
            return None
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        accessions = recent.get("accessionNumber") or []
        docs = recent.get("primaryDocument") or []
        out: list[NormalizedSecFiling] = []
        for idx, form in enumerate(forms[:limit]):
            filed = str(dates[idx]) if idx < len(dates) else ""
            accession = str(accessions[idx]) if idx < len(accessions) else None
            primary_doc = str(docs[idx]) if idx < len(docs) else None
            filing_url = None
            if accession and primary_doc:
                accession_clean = accession.replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{primary_doc}"
            out.append(
                NormalizedSecFiling(
                    symbol=symbol,
                    form=str(form),
                    filed_at=filed,
                    accession_number=accession,
                    primary_document=primary_doc,
                    filing_url=filing_url,
                    source="sec",
                )
            )
        return out or None


