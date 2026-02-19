from mcp_server.lib.formatters import FINANCIAL_DISCLAIMER, format_response, line_date, line_money


def test_format_response_includes_disclaimer() -> None:
    output = format_response("Title", ["a", "b"], source="X", warning="Y")
    assert "Title" in output
    assert "Source: X" in output
    assert "Warning: Y" in output
    assert FINANCIAL_DISCLAIMER in output


def test_line_helpers() -> None:
    assert line_money("Price", 10.123) == "Price: $10.12"
    assert line_date("Timestamp", 1700000000).startswith("Timestamp: 2023")


