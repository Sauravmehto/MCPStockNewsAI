"""Portfolio validation logic."""

from __future__ import annotations

import math

import pandas as pd

from mcp_server.portfolio.data_loader import REQUIRED_COLUMNS
from mcp_server.portfolio.models import ValidationIssue
from mcp_server.services.base import validate_symbol

VALID_BUCKETS = {"Core", "Growth", "Defensive", "Income", "Speculative"}


def _missing_columns(frame: pd.DataFrame) -> list[str]:
    return [col for col in REQUIRED_COLUMNS if col not in frame.columns]


def validate_portfolio_frame(frame: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    missing = _missing_columns(frame)
    if missing:
        for col in missing:
            issues.append(
                ValidationIssue(
                    field=col,
                    code="missing_column",
                    message=f"Required column is missing: {col}",
                )
            )
        return issues

    if frame[REQUIRED_COLUMNS].isnull().any().any():
        null_cols = [col for col in REQUIRED_COLUMNS if frame[col].isnull().any()]
        for col in null_cols:
            issues.append(ValidationIssue(field=col, code="null_value", message=f"Null values found in {col}."))

    for idx, row in frame.iterrows():
        row_num = int(idx) + 2
        symbol = str(row["Symbol"]).strip().upper()
        try:
            validate_symbol(symbol)
        except ValueError:
            issues.append(
                ValidationIssue(field="Symbol", row=row_num, code="invalid_symbol", message=f"Invalid ticker: {symbol}")
            )

        bucket = str(row["Bucket"]).strip()
        if bucket not in VALID_BUCKETS:
            issues.append(
                ValidationIssue(
                    field="Bucket",
                    row=row_num,
                    code="invalid_bucket",
                    message=f"Bucket must be one of {sorted(VALID_BUCKETS)}.",
                )
            )

        quantity = row["Quantity"]
        if not isinstance(quantity, (int, float)) or float(quantity) <= 0 or not float(quantity).is_integer():
            issues.append(
                ValidationIssue(
                    field="Quantity",
                    row=row_num,
                    code="invalid_quantity",
                    message="Quantity must be a positive integer.",
                )
            )

        entry = row["Entry_Price"]
        if not isinstance(entry, (int, float)) or float(entry) <= 0:
            issues.append(
                ValidationIssue(
                    field="Entry_Price",
                    row=row_num,
                    code="invalid_entry_price",
                    message="Entry_Price must be a positive numeric value.",
                )
            )

        target = row["Target_Weight"]
        if not isinstance(target, (int, float)) or float(target) < 0 or float(target) > 1:
            issues.append(
                ValidationIssue(
                    field="Target_Weight",
                    row=row_num,
                    code="invalid_target_weight",
                    message="Target_Weight must be a decimal between 0 and 1.",
                )
            )

    if "Target_Weight" in frame.columns:
        total_weight = float(frame["Target_Weight"].sum())
        if not math.isfinite(total_weight) or abs(total_weight - 1.0) > 0.01:
            issues.append(
                ValidationIssue(
                    field="Target_Weight",
                    code="invalid_weight_sum",
                    message=f"Target_Weight sum must be 1.0 +/- 0.01, received {total_weight:.4f}.",
                )
            )
    return issues


