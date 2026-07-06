from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from simulation.market_data.cache import (
    DEFAULT_TREASURY_CACHE_PATH,
    DEFAULT_TREASURY_META_PATH,
    DEFAULT_TREASURY_VENDORED_PATH,
    TREASURY_TENORS,
    is_cache_stale,
    resolve_cache_read_path,
    write_treasury_cache,
)
from simulation.market_data.fetch import TreasuryFetcher, treasury_real_yield_curve


def treasury_rows_with_all_tenors(
    rows: list[tuple[date, dict[str, Decimal]]],
) -> list[tuple[date, dict[str, Decimal]]]:
    return [row for row in rows if all(tenor in row[1] for tenor in TREASURY_TENORS)]


@dataclass(frozen=True)
class TreasuryYieldsResolved:
    yields: dict[str, float]
    observation_date: date


def _latest_curve(today: date, path: Path) -> tuple[date, dict[str, float]]:
    best_date: date | None = None
    best_yields: dict[str, float] | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                observed = date.fromisoformat(row["observation_date"].strip())
            except KeyError, ValueError, AttributeError:
                continue
            if observed > today:
                continue
            yields: dict[str, float] = {}
            for tenor in TREASURY_TENORS:
                cell = row.get(tenor, "")
                if cell:
                    try:
                        yields[tenor] = float(cell)
                    except ValueError:
                        continue
            if not all(tenor in yields for tenor in TREASURY_TENORS):
                continue
            if best_date is None or observed > best_date:
                best_date = observed
                best_yields = yields
    if best_date is None or best_yields is None:
        raise ValueError(f"no Treasury curve at or before {today.isoformat()}")
    return best_date, best_yields


def resolve_treasury_real_yields(
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    fetcher: TreasuryFetcher = treasury_real_yield_curve,
    cache_path: Path = DEFAULT_TREASURY_CACHE_PATH,
    meta_path: Path = DEFAULT_TREASURY_META_PATH,
    vendored_path: Path = DEFAULT_TREASURY_VENDORED_PATH,
) -> TreasuryYieldsResolved:
    today = today or date.today()
    read_path = resolve_cache_read_path(
        cache_path=cache_path, vendored_path=vendored_path
    )

    if allow_refresh:
        resolved_now = now or datetime.now(tz=UTC)
        if is_cache_stale(now=resolved_now, meta_path=meta_path):
            try:
                rows = treasury_rows_with_all_tenors(fetcher(year=resolved_now.year))
                if rows:
                    write_treasury_cache(
                        rows,
                        now=resolved_now,
                        cache_path=cache_path,
                        meta_path=meta_path,
                    )
                    read_path = resolve_cache_read_path(
                        cache_path=cache_path, vendored_path=vendored_path
                    )
            except Exception:
                pass

    observed, yields = _latest_curve(today, read_path)
    return TreasuryYieldsResolved(yields=yields, observation_date=observed)
