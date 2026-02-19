"""Normalized data models shared across providers and tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ProviderName = Literal[
    "finnhub",
    "alphavantage",
    "yahoo",
    "fmp",
    "fred",
    "newsapi",
    "sec",
    "anthropic",
    "twelvedata",
    "marketstack",
    "websearch",
]
Interval = Literal["1", "5", "15", "30", "60", "D", "W", "M"]


@dataclass
class NormalizedQuote:
    symbol: str
    price: float
    change: float
    percent_change: float
    high: float
    low: float
    open: float
    previous_close: float
    timestamp: int | None
    source: ProviderName


@dataclass
class NormalizedCompanyProfile:
    symbol: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    country: str | None = None
    industry: str | None = None
    ipo: str | None = None
    market_capitalization: float | None = None
    website: str | None = None
    logo: str | None = None
    source: ProviderName = "finnhub"


@dataclass
class NormalizedCandle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class NormalizedNewsItem:
    headline: str
    summary: str | None = None
    url: str | None = None
    source: str | None = None
    datetime: int | None = None


@dataclass
class NormalizedRsiPoint:
    timestamp: int
    value: float


@dataclass
class NormalizedMacdPoint:
    timestamp: int
    macd: float
    signal: float
    histogram: float


@dataclass
class NormalizedKeyFinancials:
    symbol: str
    pe_ratio: float | None = None
    eps: float | None = None
    book_value: float | None = None
    dividend_yield: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    market_capitalization: float | None = None
    beta: float | None = None
    source: ProviderName = "finnhub"


@dataclass
class NormalizedDividendEvent:
    symbol: str
    ex_date: str | None = None
    payment_date: str | None = None
    amount: float | None = None
    source: ProviderName = "fmp"


@dataclass
class NormalizedSplitEvent:
    symbol: str
    date: str | None = None
    ratio: str | None = None
    source: ProviderName = "fmp"


@dataclass
class NormalizedEarningsEvent:
    symbol: str
    date: str | None = None
    eps_estimate: float | None = None
    eps_actual: float | None = None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None
    source: ProviderName = "fmp"


@dataclass
class NormalizedOptionsContract:
    symbol: str
    expiration: str
    strike: float
    call_put: Literal["call", "put"]
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    source: ProviderName = "yahoo"


@dataclass
class NormalizedSecFiling:
    symbol: str
    form: str
    filed_at: str
    accession_number: str | None = None
    primary_document: str | None = None
    filing_url: str | None = None
    source: ProviderName = "sec"


@dataclass
class NormalizedStatement:
    symbol: str
    statement_type: Literal["income", "balance", "cashflow"]
    period: str | None = None
    values: dict[str, float | int | str | None] | None = None
    source: ProviderName = "fmp"


@dataclass
class NormalizedMetricsSnapshot:
    symbol: str
    metrics: dict[str, Any]
    source: ProviderName = "finnhub"


