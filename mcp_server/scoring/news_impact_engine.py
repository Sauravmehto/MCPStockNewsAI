"""Portfolio news impact scoring engine."""

from __future__ import annotations

import re
from typing import Protocol


class _SummaryModel(Protocol):
    def generate_summary(self, prompt: str) -> str | None:
        """Return a concise model response."""


SECTOR_NEWS_MAP: dict[str, list[str]] = {
    "iran war": ["Energy", "Defense", "Airlines"],
    "dedollarization": ["Financials", "Gold", "Crypto"],
    "trade deal": ["Technology", "Consumer Discretionary"],
    "chip ban": ["Technology", "Semiconductors"],
    "fed rate hike": ["Financials", "Real Estate", "Utilities"],
    "ai release": ["Technology", "Communication Services"],
    "budget": ["Healthcare", "Defense", "Infrastructure"],
    "oil spike": ["Energy", "Airlines", "Consumer Staples"],
}

STOCK_SECTOR_MAP: dict[str, str] = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Technology",
    "TSLA": "Consumer Discretionary",
    "META": "Communication Services",
    "JNJ": "Healthcare",
    "PG": "Consumer Staples",
    "KO": "Consumer Staples",
}

SECTOR_SYMBOL_MAP: dict[str, set[str]] = {
    "Technology": {"AAPL", "MSFT", "NVDA", "AMD", "ORCL", "ADBE", "CSCO", "QCOM"},
    "Healthcare": {"UNH", "JNJ", "LLY", "PFE", "MRK", "ABBV", "TMO", "AMGN"},
    "Financials": {"JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "BLK"},
    "Energy": {"XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "OXY"},
    "Consumer Discretionary": {"AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "BKNG"},
    "Communication Services": {"GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS"},
    "Industrials": {"GE", "CAT", "UNP", "RTX", "HON", "UPS", "BA", "LMT"},
    "Utilities": {"NEE", "DUK", "SO", "AEP", "EXC", "SRE", "XEL", "ED"},
    "Materials": {"LIN", "APD", "SHW", "ECL", "NEM", "FCX", "DOW", "NUE"},
    "Real Estate": {"AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "WELL", "DLR"},
    "Consumer Staples": {"PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL"},
}

SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Technology": ("technology", "semiconductor", "software", "cloud", "ai", "data center", "chip"),
    "Healthcare": ("healthcare", "biotech", "drug", "clinical", "fda", "medical"),
    "Financials": ("bank", "lending", "credit", "broker", "insurance", "financial"),
    "Energy": ("oil", "gas", "refining", "drilling", "energy", "opec"),
    "Consumer Discretionary": ("consumer spending", "retail", "automotive", "ecommerce", "travel"),
    "Communication Services": ("advertising", "media", "streaming", "telecom", "social media"),
    "Industrials": ("industrial", "aerospace", "defense", "freight", "machinery", "manufacturing"),
    "Utilities": ("utility", "power grid", "electricity", "renewable utility"),
    "Materials": ("materials", "chemicals", "metals", "mining", "commodities"),
    "Real Estate": ("reit", "commercial real estate", "rental", "property"),
    "Consumer Staples": ("consumer staples", "beverage", "household", "grocery"),
}

MACRO_KEYWORDS: tuple[str, ...] = (
    "inflation",
    "interest rate",
    "fed",
    "federal reserve",
    "tariff",
    "recession",
    "geopolitical",
    "jobs report",
    "cpi",
    "gdp",
    "treasury yield",
)

POSITIVE_WORDS = {
    "beat",
    "strong",
    "surge",
    "growth",
    "upgrade",
    "bullish",
    "record",
    "profit",
    "partnership",
    "wins",
    "expands",
}
NEGATIVE_WORDS = {
    "miss",
    "weak",
    "drop",
    "decline",
    "downgrade",
    "bearish",
    "loss",
    "lawsuit",
    "probe",
    "cuts",
    "layoffs",
    "warning",
}


def infer_sector(symbol: str, profile_industry: str | None = None) -> str:
    """Infer a broad sector from symbol map and optional profile industry text."""
    cleaned_symbol = symbol.upper().strip()
    mapped = STOCK_SECTOR_MAP.get(cleaned_symbol)
    if mapped:
        return mapped
    for sector, symbols in SECTOR_SYMBOL_MAP.items():
        if cleaned_symbol in symbols:
            return sector
    if not profile_industry:
        return "Unknown"
    industry = profile_industry.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(keyword in industry for keyword in keywords):
            return sector
    return "Unknown"


def classify_sentiment(text: str, anthropic_client: _SummaryModel | None = None) -> int:
    """Classify sentiment using Anthropic when available, with deterministic fallback."""
    cleaned = " ".join(text.split())
    if anthropic_client:
        prompt = (
            "Classify sentiment for portfolio risk as exactly one token: POSITIVE, NEGATIVE, or NEUTRAL.\n"
            f"Text: {cleaned}"
        )
        try:
            model_response = (anthropic_client.generate_summary(prompt) or "").upper()
            if "NEGATIVE" in model_response:
                return -1
            if "POSITIVE" in model_response:
                return 1
            if "NEUTRAL" in model_response:
                return 0
        except Exception:
            pass
    lower = cleaned.lower()
    positive_hits = sum(1 for word in POSITIVE_WORDS if re.search(rf"\b{re.escape(word)}\b", lower))
    negative_hits = sum(1 for word in NEGATIVE_WORDS if re.search(rf"\b{re.escape(word)}\b", lower))
    if negative_hits > positive_hits:
        return -1
    if positive_hits > negative_hits:
        return 1
    return 0


def get_affected_sectors(news_item: str) -> list[str]:
    """Map a news item to affected sectors using keyword matching."""
    lower = news_item.lower()
    affected: list[str] = []
    for keyword, sectors in SECTOR_NEWS_MAP.items():
        if keyword in lower:
            for sector in sectors:
                if sector not in affected:
                    affected.append(sector)
    return affected


def is_macro_relevant(news_item: str) -> bool:
    """Return True if the headline is broad macro news."""
    lower = news_item.lower()
    return any(keyword in lower for keyword in MACRO_KEYWORDS)


def map_sector_exposure(sector: str, news_item: str) -> bool:
    """Return True when the symbol's sector is listed as affected by a headline."""
    return sector in get_affected_sectors(news_item)


def score_relevance(symbol: str, sector: str, news_item: str) -> int:
    """Score relevance with the requested 0-3 scale."""
    lower = news_item.lower()
    if symbol.lower() in lower:
        return 3
    if map_sector_exposure(sector, news_item):
        return 2
    if is_macro_relevant(news_item):
        return 1
    return 0


def apply_beta_multiplier(base_impact: float, beta: float) -> float:
    """Apply beta amplification to a base impact value."""
    return base_impact * abs(beta)


def estimate_price_impact_pct(relevance: int, sentiment: int, beta: float) -> float:
    """Estimate directional percent impact using the requested formula."""
    base_impact = relevance * 0.5
    beta_adjusted = apply_beta_multiplier(base_impact, beta)
    directional = beta_adjusted * sentiment
    return round(directional, 2)


def calculate_dollar_impact(qty: float, price: float, directional_pct: float) -> float:
    """Calculate dollar impact from qty, price, and directional percent move."""
    return round(qty * price * (directional_pct / 100.0), 2)


def get_action(relevance: int, sentiment: int, beta: float) -> str:
    """Classify action labels exactly as requested."""
    if relevance >= 2 and sentiment < 0 and beta > 1.5:
        return "🔴 REDUCE"
    if relevance >= 2 and sentiment < 0:
        return "🟠 WATCH"
    if relevance >= 1 and sentiment < 0:
        return "🟡 MONITOR"
    return "🟢 HOLD"


def score_news_impact(
    symbol: str,
    news_item: str,
    price: float,
    beta: float,
    qty: float,
    anthropic_client: _SummaryModel | None = None,
) -> dict[str, object]:
    """Score one news item against one stock."""
    sector = infer_sector(symbol=symbol)
    relevance = score_relevance(symbol=symbol, sector=sector, news_item=news_item)
    sentiment = classify_sentiment(news_item, anthropic_client=anthropic_client)
    estimated_pct_impact = estimate_price_impact_pct(relevance=relevance, sentiment=sentiment, beta=beta)
    estimated_dollar_impact = calculate_dollar_impact(qty=qty, price=price, directional_pct=estimated_pct_impact)
    risk_score = round(relevance * abs(beta), 2)
    return {
        "symbol": symbol,
        "sector": sector,
        "news_item": news_item,
        "relevance": relevance,
        "sentiment": sentiment,
        "estimated_pct_impact": estimated_pct_impact,
        "estimated_dollar_impact": estimated_dollar_impact,
        "risk_score": risk_score,
        "action": get_action(relevance, sentiment, beta),
        "quantity": round(qty, 4),
        "price": round(price, 4),
        "beta": round(beta, 4),
    }


def score_symbol_news_impact(
    symbol: str,
    quantity: float,
    price: float,
    beta: float,
    sector: str,
    news_items: list[str],
    anthropic_client: _SummaryModel | None = None,
) -> dict[str, object]:
    """Aggregate multiple headlines into a symbol-level ranked risk row."""
    clean_items = [item.strip() for item in news_items if item and item.strip()]
    item_scores = [
        score_news_impact(symbol=symbol, news_item=item, beta=beta, qty=quantity, price=price, anthropic_client=anthropic_client)
        for item in clean_items[:30]
    ]
    if not item_scores:
        return {
            "symbol": symbol,
            "sector": sector,
            "quantity": round(quantity, 4),
            "price": round(price, 4),
            "beta": round(beta, 4),
            "news_count": 0,
            "weighted_risk_score": 0.0,
            "estimated_percent_impact": 0.0,
            "estimated_dollar_impact": 0.0,
            "action": "🟢 HOLD",
            "items": [],
        }

    negative_items = [item for item in item_scores if int(item["sentiment"]) < 0]
    weighted_risk_score = max((float(item["risk_score"]) for item in negative_items), default=0.0)
    estimated_percent_impact = sum(float(item["estimated_pct_impact"]) for item in item_scores) / len(item_scores)
    estimated_dollar_impact = sum(float(item["estimated_dollar_impact"]) for item in item_scores)
    top_action = "🟢 HOLD"
    for candidate in ("🔴 REDUCE", "🟠 WATCH", "🟡 MONITOR"):
        if any(item["action"] == candidate for item in item_scores):
            top_action = candidate
            break

    return {
        "symbol": symbol,
        "sector": sector,
        "quantity": round(quantity, 4),
        "price": round(price, 4),
        "beta": round(beta, 4),
        "news_count": len(item_scores),
        "weighted_risk_score": round(weighted_risk_score, 2),
        "estimated_percent_impact": round(estimated_percent_impact, 2),
        "estimated_dollar_impact": round(estimated_dollar_impact, 2),
        "action": top_action,
        "items": item_scores,
    }


def rank_symbol_impacts(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Sort symbol rows descending by risk score."""
    return sorted(rows, key=lambda row: float(row.get("weighted_risk_score", 0.0)), reverse=True)


