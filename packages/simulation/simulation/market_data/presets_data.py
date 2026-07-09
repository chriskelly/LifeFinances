from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"
_CAPE_REGRESSION_PATH = _DATA_DIR / "cape_regression_v7.json"
_VARIANCE_TABLE_PATH = _DATA_DIR / "stock_log_variance_by_block.csv"

# tpaw ordering: full then restricted, each [5, 10, 20, 30]-year.
REGRESSION_KEYS = (
    "full_5",
    "full_10",
    "full_20",
    "full_30",
    "restricted_5",
    "restricted_10",
    "restricted_20",
    "restricted_30",
)


@dataclass(frozen=True)
class CapeRegression:
    shiller_10yr_real_earnings: float
    pairs: dict[str, tuple[float, float]]  # key -> (slope, intercept)
    effective_date: str


@lru_cache(maxsize=1)
def load_cape_regression() -> CapeRegression:
    data = json.loads(_CAPE_REGRESSION_PATH.read_text(encoding="utf-8"))
    raw = data["regression_coeffs"]
    pairs = {key: (float(raw[key][0]), float(raw[key][1])) for key in REGRESSION_KEYS}
    return CapeRegression(
        shiller_10yr_real_earnings=float(data["shiller_10yr_real_earnings"]),
        pairs=pairs,
        effective_date=str(data["effective_date"]),
    )


@lru_cache(maxsize=1)
def load_stock_log_variance_by_block() -> dict[int, float]:
    table: dict[int, float] = {}
    with _VARIANCE_TABLE_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            table[int(row["block_size"])] = float(row["annual_log_returns_variance"])
    return table
