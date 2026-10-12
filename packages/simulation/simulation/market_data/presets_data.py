from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Literal, NamedTuple

_DATA_DIR = Path(__file__).parent / "data"
_CAPE_REGRESSION_PATH = _DATA_DIR / "cape_regression_v8.json"

# Asset key -> vendored empirical-stats-by-block filename.
_ASSET_TABLE_PATHS = {
    "stocks": _DATA_DIR / "stock_empirical_stats_by_block.csv",
    "bonds": _DATA_DIR / "bond_empirical_stats_by_block.csv",
}

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
    effective_date: date


@lru_cache(maxsize=1)
def load_cape_regression() -> CapeRegression:
    data = json.loads(_CAPE_REGRESSION_PATH.read_text(encoding="utf-8"))
    raw = data["regression_coeffs"]
    pairs = {key: (float(raw[key][0]), float(raw[key][1])) for key in REGRESSION_KEYS}
    return CapeRegression(
        shiller_10yr_real_earnings=float(data["shiller_10yr_real_earnings"]),
        pairs=pairs,
        effective_date=date.fromisoformat(str(data["effective_date"])),
    )


class EmpiricalStats(NamedTuple):
    # tpaw EmpiricalStats32: annual_non_log_returns_mean (simple) and
    # annual_log_returns_variance (log). The bases differ — keep them explicit.
    annual_non_log_mean: float
    annual_log_variance: float


@lru_cache(maxsize=2)
def load_empirical_stats_by_block(
    asset: Literal["stocks", "bonds"],
) -> Mapping[int, EmpiricalStats]:
    if asset not in _ASSET_TABLE_PATHS:
        known = ", ".join(sorted(_ASSET_TABLE_PATHS))
        raise ValueError(f"unknown asset {asset!r} (known assets: {known})")
    table: dict[int, EmpiricalStats] = {}
    with _ASSET_TABLE_PATHS[asset].open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            table[int(row["block_size"])] = EmpiricalStats(
                annual_non_log_mean=float(row["annual_non_log_returns_mean"]),
                annual_log_variance=float(row["annual_log_returns_variance"]),
            )
    return MappingProxyType(table)


def empirical_stats(
    *, asset: Literal["stocks", "bonds"], block_size: int
) -> EmpiricalStats:
    # A plan block size outside the vendored table is a ValueError, not a bare KeyError.
    table = load_empirical_stats_by_block(asset)
    if block_size not in table:
        raise ValueError(
            f"no vendored {asset} empirical stats for block size {block_size} "
            f"(table covers {min(table)}..{max(table)})"
        )
    return table[block_size]
