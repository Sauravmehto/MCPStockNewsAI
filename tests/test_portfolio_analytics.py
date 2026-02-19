import pandas as pd

from mcp_server.portfolio.analytics_core import (
    calculate_bucket_distribution,
    calculate_total_portfolio_value,
    calculate_total_return_percent,
    calculate_unrealized_pnl,
    enrich_with_market_values,
)


def test_portfolio_core_metrics() -> None:
    frame = pd.DataFrame(
        [
            {"Symbol": "AAPL", "Bucket": "Core", "Quantity": 10, "Entry_Price": 100.0, "Target_Weight": 0.5},
            {"Symbol": "MSFT", "Bucket": "Growth", "Quantity": 5, "Entry_Price": 200.0, "Target_Weight": 0.5},
        ]
    )
    enriched = enrich_with_market_values(frame, {"AAPL": 120.0, "MSFT": 180.0})
    assert calculate_total_portfolio_value(enriched) == 2100.0
    assert calculate_unrealized_pnl(enriched) == 100.0
    assert calculate_total_return_percent(enriched) == 5.0
    buckets = calculate_bucket_distribution(enriched)
    assert round(sum(buckets.values()), 6) == 1.0


