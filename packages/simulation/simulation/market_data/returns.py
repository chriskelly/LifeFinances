from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np

_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_RETURNS_CSV = _DATA_DIR / "v8_real_monthly_returns.csv"
V8_EFFECTIVE_DATE = date(2026, 7, 27)


@dataclass(frozen=True, eq=False)
class HistoricalReturns:
    stocks_log: np.ndarray
    bonds_log: np.ndarray
    start: tuple[int, int]
    effective_date: date

    @property
    def length(self) -> int:
        return int(self.stocks_log.shape[0])


def _load_from_csv(
    path: Path, *, effective_date: date = V8_EFFECTIVE_DATE
) -> HistoricalReturns:
    years: list[int] = []
    months: list[int] = []
    stocks: list[float] = []
    bonds: list[float] = []
    # utf-8-sig strips the BOM present in the vendored tpaw CSV.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            years.append(int(row["year"]))
            months.append(int(row["month"]))
            stocks.append(float(row["stock real return"]))
            bonds.append(float(row["bond real return"]))

    stocks_non_log = np.asarray(stocks, dtype=np.float64)
    bonds_non_log = np.asarray(bonds, dtype=np.float64)
    if stocks_non_log.size == 0:
        raise ValueError(f"no monthly returns rows in {path}")
    return HistoricalReturns(
        stocks_log=np.log1p(stocks_non_log),
        bonds_log=np.log1p(bonds_non_log),
        start=(years[0], months[0]),
        effective_date=effective_date,
    )


@lru_cache(maxsize=1)
def load_historical_returns() -> HistoricalReturns:
    return _load_from_csv(_DEFAULT_RETURNS_CSV)
