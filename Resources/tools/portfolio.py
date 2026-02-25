"""Portfolio file parsing helpers for CSV/XLS/XLSX uploads."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass

SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


@dataclass
class PortfolioHolding:
    symbol: str
    quantity: float
    avg_cost: float | None = None
    notes: str | None = None


def normalize_header(header: str) -> str:
    return re.sub(r"[\s_\-./]+", "", header.strip().lower())


def to_finite_number(value: object) -> float | None:
    if isinstance(value, (int, float)):
        out = float(value)
        return out if out == out and out not in {float("inf"), float("-inf")} else None
    if isinstance(value, str):
        cleaned = re.sub(r"[$,%\s,]", "", value)
        if not cleaned:
            return None
        try:
            out = float(cleaned)
        except ValueError:
            return None
        return out if out == out and out not in {float("inf"), float("-inf")} else None
    return None


def find_field(row: dict[str, object], aliases: list[str]) -> object | None:
    alias_set = set(aliases)
    for key, value in row.items():
        if normalize_header(str(key)) in alias_set:
            return value
    return None


def validate_symbol(value: object, row_index: int) -> str:
    symbol = str(value or "").strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise ValueError(
            f"Row {row_index}: invalid symbol. Expected a ticker-like value in column symbol/ticker."
        )
    return symbol


def normalize_portfolio_holding(row: dict[str, object], row_index: int) -> PortfolioHolding:
    symbol_raw = find_field(row, ["symbol", "ticker", "stock", "code"])
    qty_raw = find_field(row, ["quantity", "qty", "shares", "units"])
    avg_cost_raw = find_field(
        row,
        ["avgcost", "averagecost", "avgprice", "averageprice", "costbasis", "buyprice", "entryprice"],
    )
    notes_raw = find_field(row, ["note", "notes", "comment", "comments"])
    symbol = validate_symbol(symbol_raw, row_index)
    quantity = to_finite_number(qty_raw)
    if quantity is None or quantity <= 0:
        raise ValueError(
            f"Row {row_index}: invalid quantity. Expected a positive number in quantity/qty/shares."
        )
    avg_cost = to_finite_number(avg_cost_raw)
    notes = None
    if notes_raw is not None:
        text = str(notes_raw).strip()
        notes = text or None
    return PortfolioHolding(symbol=symbol, quantity=quantity, avg_cost=avg_cost, notes=notes)


def rows_from_csv(content: str) -> list[dict[str, object]]:
    stripped = [line.strip() for line in content.splitlines() if line.strip()]
    if not stripped:
        return []
    reader = csv.DictReader(stripped)
    rows: list[dict[str, object]] = []
    for row in reader:
        rows.append({k: v for k, v in row.items()})
    return rows


def rows_from_excel(absolute_file_path: str, sheet_name: str | None = None) -> list[dict[str, object]]:
    try:
        import pandas as pd

        frame = pd.read_excel(absolute_file_path, sheet_name=sheet_name or 0)
    except ValueError as error:
        raise ValueError(str(error)) from error
    except ImportError as error:
        raise ValueError(
            "Excel parsing requires pandas/openpyxl/xlrd dependencies. Install requirements.txt."
        ) from error
    return frame.fillna("").to_dict(orient="records")


def load_portfolio_holdings_from_file(portfolio_file_path: str, sheet_name: str | None = None) -> list[PortfolioHolding]:
    absolute_file_path = (
        portfolio_file_path if os.path.isabs(portfolio_file_path) else os.path.abspath(portfolio_file_path)
    )
    ext = os.path.splitext(absolute_file_path)[1].lower()
    rows: list[dict[str, object]]
    if ext == ".csv":
        with open(absolute_file_path, "r", encoding="utf-8") as handle:
            rows = rows_from_csv(handle.read())
    elif ext in {".xlsx", ".xls"}:
        rows = rows_from_excel(absolute_file_path, sheet_name)
    else:
        raise ValueError(f"Unsupported portfolio file type: {ext or 'unknown'}. Use .csv, .xlsx, or .xls.")
    if not rows:
        raise ValueError("Portfolio file has no data rows.")
    holdings: list[PortfolioHolding] = []
    row_errors: list[str] = []
    for idx, row in enumerate(rows):
        try:
            holdings.append(normalize_portfolio_holding(row, idx + 2))
        except ValueError as error:
            row_errors.append(str(error))
    if not holdings:
        raise ValueError(f"No valid holdings found. {' | '.join(row_errors[:5])}")
    if row_errors:
        raise ValueError(f"Some rows are invalid. Fix file and retry. {' | '.join(row_errors[:5])}")
    return holdings


