import pandas as pd

from mcp_server.portfolio.validation import validate_portfolio_frame


def test_portfolio_validation_rejects_weight_sum() -> None:
    frame = pd.DataFrame(
        [
            {"Symbol": "AAPL", "Bucket": "Core", "Quantity": 10, "Entry_Price": 100.0, "Target_Weight": 0.7},
            {"Symbol": "MSFT", "Bucket": "Growth", "Quantity": 10, "Entry_Price": 100.0, "Target_Weight": 0.2},
        ]
    )
    issues = validate_portfolio_frame(frame)
    assert any(issue.code == "invalid_weight_sum" for issue in issues)


def test_portfolio_validation_accepts_valid_frame() -> None:
    frame = pd.DataFrame(
        [
            {"Symbol": "AAPL", "Bucket": "Core", "Quantity": 10, "Entry_Price": 100.0, "Target_Weight": 0.5},
            {"Symbol": "MSFT", "Bucket": "Growth", "Quantity": 5, "Entry_Price": 200.0, "Target_Weight": 0.5},
        ]
    )
    issues = validate_portfolio_frame(frame)
    assert not issues


