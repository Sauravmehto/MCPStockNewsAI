from mcp_server.scoring.news_impact_engine import (
    classify_sentiment,
    get_action,
    score_relevance,
    score_news_impact,
)


def test_sentiment_fallback_is_deterministic() -> None:
    assert classify_sentiment("Company reports strong growth and record profit") == 1
    assert classify_sentiment("Company issues warning after weak demand and layoffs") == -1
    assert classify_sentiment("Company hosts investor day next month") == 0


def test_relevance_priority_symbol_then_sector_then_macro() -> None:
    assert score_relevance("AAPL", "Technology", "AAPL launches new AI chip") == 3
    assert score_relevance("AAPL", "Technology", "Fed signals inflation is cooling") == 1
    assert score_relevance("AAPL", "Technology", "chip ban pressure for semiconductors grows") == 2


def test_score_news_impact_outputs_action_and_dollar_impact() -> None:
    payload = score_news_impact(
        symbol="TSLA",
        news_item="TSLA faces lawsuit after weak deliveries and profit warning",
        price=200.0,
        beta=1.8,
        qty=12,
    )
    assert payload["risk_score"] > 0
    assert payload["estimated_pct_impact"] < 0
    assert payload["estimated_dollar_impact"] < 0
    assert payload["action"] in {"🔴 REDUCE", "🟠 WATCH", "🟡 MONITOR", "🟢 HOLD"}
    assert get_action(int(payload["relevance"]), int(payload["sentiment"]), float(payload["beta"])) == payload["action"]


