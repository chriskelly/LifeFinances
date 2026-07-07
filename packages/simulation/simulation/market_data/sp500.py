from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from simulation.market_data.cache import (
    DEFAULT_SP500_CACHE_PATH,
    DEFAULT_SP500_META_PATH,
    DEFAULT_SP500_VENDORED_PATH,
    MarketDataSource,
    is_cache_stale,
    resolve_cache_read_path,
    write_sp500_cache,
)
from simulation.market_data.fetch import LOOKBACK_DAYS, EodCloseFetcher, eod_gspc_close


@dataclass(frozen=True)
class SP500Resolved:
    close: float
    observation_date: date
    source: MarketDataSource


def _latest_close(today: date, path: Path) -> tuple[date, float]:
    best_date: date | None = None
    best_close: float | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                observed = date.fromisoformat(row["observation_date"].strip())
                close = float(row["close"])
            except KeyError, ValueError, AttributeError:
                continue
            if observed > today:
                continue
            if best_date is None or observed > best_date:
                best_date = observed
                best_close = close
    if best_date is None or best_close is None:
        raise ValueError(f"no S&P close at or before {today.isoformat()}")
    return best_date, best_close


def _resolve_source(
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


def resolve_latest_sp500_close(
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    api_key: str | None = None,
    fetcher: EodCloseFetcher = eod_gspc_close,
    cache_path: Path = DEFAULT_SP500_CACHE_PATH,
    meta_path: Path = DEFAULT_SP500_META_PATH,
    vendored_path: Path = DEFAULT_SP500_VENDORED_PATH,
    lookback_days: int = LOOKBACK_DAYS,
) -> SP500Resolved:
    today = today or date.today()
    read_path = resolve_cache_read_path(
        cache_path=cache_path, vendored_path=vendored_path
    )
    refreshed_live = False

    if allow_refresh and api_key:
        resolved_now = now or datetime.now(tz=UTC)
        if is_cache_stale(now=resolved_now, meta_path=meta_path):
            try:
                pairs = fetcher(
                    api_key=api_key,
                    from_date=resolved_now.date() - timedelta(days=lookback_days),
                )
                if pairs:
                    write_sp500_cache(
                        pairs,
                        now=resolved_now,
                        cache_path=cache_path,
                        meta_path=meta_path,
                    )
                    read_path = resolve_cache_read_path(
                        cache_path=cache_path, vendored_path=vendored_path
                    )
                    refreshed_live = True
            except Exception:
                pass

    try:
        observed, close = _latest_close(today, read_path)
    except ValueError:
        if read_path == vendored_path:
            raise
        read_path = vendored_path
        refreshed_live = False
        observed, close = _latest_close(today, read_path)
    source = _resolve_source(
        refreshed_live=refreshed_live,
        read_path=read_path,
        cache_path=cache_path,
    )
    return SP500Resolved(close=close, observation_date=observed, source=source)
