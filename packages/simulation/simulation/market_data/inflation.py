from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Literal

from core.models import Plan

from simulation.market_data.cache import (
    DEFAULT_T10YIE_CACHE_PATH,
    DEFAULT_T10YIE_META_PATH,
    MarketDataSource,
    is_t10yie_cache_stale,
    resolve_t10yie_read_path,
    write_t10yie_cache,
)
from simulation.market_data.fetch import LOOKBACK_DAYS, fred_observations

_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_T10YIE_CSV = _DATA_DIR / "t10yie_daily.csv"
T10YIEFetcher = Callable[..., list[tuple[date, Decimal]]]


@dataclass(frozen=True)
class InflationResolved:
    annual: float
    monthly: float
    source: Literal["suggested", "manual"]
    market_source: MarketDataSource | None = None
    observation_date: date | None = None


def annual_to_monthly(annual: float) -> float:
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def _round_half_away(value: Decimal, places: str = "0.001") -> Decimal:
    # ROUND_HALF_UP rounds half away from zero, matching Rust f64::round (tpaw RoundP).
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _suggested_annual(today: date, path: Path) -> tuple[float, date]:
    best_date: date | None = None
    best_value: Decimal | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                observed = date.fromisoformat(row[0].strip())
                percent = Decimal(row[1].strip())
            except ValueError, ArithmeticError:
                continue
            if observed > today:
                continue
            if best_date is None or observed > best_date:
                best_date = observed
                best_value = percent
    if best_value is None or best_date is None:
        raise ValueError(f"no T10YIE observation at or before {today.isoformat()}")
    annual = float(_round_half_away(best_value / Decimal(100)))
    return annual, best_date


def _market_source(
    *,
    refreshed_live: bool,
    read_path: Path,
    cache_path: Path,
) -> MarketDataSource:
    if refreshed_live:
        return "live"
    if read_path == cache_path and cache_path.is_file():
        return "cache"
    return "vendored"


def _resolve_t10yie_path(
    *,
    t10yie_path: Path | None,
    allow_refresh: bool,
    now: datetime | None,
    api_key: str | None,
    fetcher: T10YIEFetcher,
    t10yie_cache_path: Path,
    t10yie_meta_path: Path,
) -> tuple[Path, bool]:
    vendored_path = t10yie_path or _DEFAULT_T10YIE_CSV
    default_path_mode = t10yie_path is None
    read_path = (
        resolve_t10yie_read_path(
            cache_path=t10yie_cache_path,
            vendored_path=vendored_path,
        )
        if default_path_mode
        else vendored_path
    )
    refreshed_live = False

    if not allow_refresh or not api_key:
        return read_path, refreshed_live

    resolved_now = now or datetime.now(tz=UTC)
    if default_path_mode and not is_t10yie_cache_stale(
        now=resolved_now,
        meta_path=t10yie_meta_path,
    ):
        return read_path, refreshed_live

    try:
        pairs = fetcher(
            api_key=api_key,
            observation_start=resolved_now.date() - timedelta(days=LOOKBACK_DAYS),
        )
        if not pairs:
            return read_path, refreshed_live
        write_t10yie_cache(
            pairs,
            now=resolved_now,
            cache_path=t10yie_cache_path,
            meta_path=t10yie_meta_path,
        )
        refreshed_live = True
    except Exception:
        return read_path, refreshed_live

    return (
        resolve_t10yie_read_path(
            cache_path=t10yie_cache_path,
            vendored_path=vendored_path,
        ),
        refreshed_live,
    )


def resolve_inflation(
    plan: Plan,
    *,
    today: date | None = None,
    t10yie_path: Path | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    api_key: str | None = None,
    fetcher: T10YIEFetcher = fred_observations,
    t10yie_cache_path: Path = DEFAULT_T10YIE_CACHE_PATH,
    t10yie_meta_path: Path = DEFAULT_T10YIE_META_PATH,
) -> InflationResolved:
    today = today or date.today()
    market_source: MarketDataSource | None = None
    observation_date: date | None = None
    if plan.inflation.mode == "manual":
        rate = plan.inflation.manual_annual_rate
        if rate is None:
            raise ValueError("manual inflation mode requires manual_annual_rate")
        annual = float(rate)
        source: Literal["suggested", "manual"] = "manual"
    else:
        vendored_path = t10yie_path or _DEFAULT_T10YIE_CSV
        path, refreshed_live = _resolve_t10yie_path(
            t10yie_path=t10yie_path,
            allow_refresh=allow_refresh,
            now=now,
            api_key=api_key,
            fetcher=fetcher,
            t10yie_cache_path=t10yie_cache_path,
            t10yie_meta_path=t10yie_meta_path,
        )
        try:
            annual, observation_date = _suggested_annual(today, path)
        except ValueError:
            if path == vendored_path:
                raise
            path = vendored_path
            refreshed_live = False
            annual, observation_date = _suggested_annual(today, path)
        market_source = _market_source(
            refreshed_live=refreshed_live,
            read_path=path,
            cache_path=t10yie_cache_path,
        )
        source = "suggested"
    return InflationResolved(
        annual=annual,
        monthly=annual_to_monthly(annual),
        source=source,
        market_source=market_source,
        observation_date=observation_date,
    )
