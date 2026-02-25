"""Portfolio file loading helpers."""

from __future__ import annotations

import os

import pandas as pd

REQUIRED_COLUMNS = ["Symbol", "Bucket", "Quantity", "Entry_Price", "Target_Weight"]


def load_portfolio_excel(file_path: str) -> pd.DataFrame:
    absolute_path = file_path if os.path.isabs(file_path) else os.path.abspath(file_path)
    ext = os.path.splitext(absolute_path)[1].lower()
    if ext not in {".xlsx", ".xls"}:
        raise ValueError("Portfolio input must be an Excel file (.xlsx or .xls).")
    frame = pd.read_excel(absolute_path, sheet_name=0)
    return frame


