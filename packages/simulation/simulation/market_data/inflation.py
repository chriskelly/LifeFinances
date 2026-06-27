from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Literal

from core.models import Plan

_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_T10YIE_CSV = _DATA_DIR / "t10yie_daily.csv"


@dataclass(frozen=True)
class InflationResolved:
    annual: float
    monthly: float
    source: Literal["suggested", "manual"]


def annual_to_monthly(annual: float) -> float:
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def _round_half_away(value: Decimal, places: str = "0.001") -> Decimal:
    # ROUND_HALF_UP rounds half away from zero, matching Rust f64::round (tpaw RoundP).
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _suggested_annual(today: date, path: Path) -> float:
    best_date: date | None = None
    best_value: Decimal | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader, None)  # header
        for row in reader:
            if len(row) < 2:
                continue
            try:
                observed = date.fromisoformat(row[0].strip())
                percent = Decimal(row[1].strip())  # raises for "." / blanks
            except ValueError, ArithmeticError:
                continue
            if observed > today:
                continue
            if best_date is None or observed > best_date:
                best_date = observed
                best_value = percent
    if best_value is None:
        raise ValueError(f"no T10YIE observation at or before {today.isoformat()}")
    return float(_round_half_away(best_value / Decimal(100)))


def resolve_inflation(
    plan: Plan,
    *,
    today: date | None = None,
    t10yie_path: Path | None = None,
) -> InflationResolved:
    today = today or date.today()
    if plan.inflation.mode == "manual":
        rate = plan.inflation.manual_annual_rate
        if rate is None:
            raise ValueError("manual inflation mode requires manual_annual_rate")
        annual = float(rate)
        source: Literal["suggested", "manual"] = "manual"
    else:
        annual = _suggested_annual(today, t10yie_path or _DEFAULT_T10YIE_CSV)
        source = "suggested"
    return InflationResolved(
        annual=annual, monthly=annual_to_monthly(annual), source=source
    )
