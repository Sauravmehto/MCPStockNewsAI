"""Typed portfolio models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Bucket = Literal["Core", "Growth", "Defensive", "Income", "Speculative"]


@dataclass
class PortfolioRow:
    symbol: str
    bucket: Bucket
    quantity: int
    entry_price: float
    target_weight: float


@dataclass
class ValidationIssue:
    field: str
    message: str
    row: int | None = None
    code: str = "invalid_value"


