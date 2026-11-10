from __future__ import annotations

import contextlib
import csv
import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from operator import itemgetter
from pathlib import Path
from typing import Literal, TextIO

from core.paths import repo_root

from simulation.market_data.fetch import (
    EOD_SP500_SYMBOL,
    FRED_T10YIE_SERIES_ID,
    TREASURY_REAL_YIELD_TYPE,
)

MarketDataSource = Literal["live", "cache", "vendored"]

CACHE_TTL = timedelta(hours=24)
_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_T10YIE_VENDORED_PATH = _DATA_DIR / "t10yie_daily.csv"
DEFAULT_MARKET_CACHE_DIR = repo_root() / "data" / "market_cache"
DEFAULT_T10YIE_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "t10yie_daily.csv"
DEFAULT_T10YIE_META_PATH = DEFAULT_MARKET_CACHE_DIR / "t10yie_daily.meta.json"


def write_t10yie_cache(
    pairs: list[tuple[date, Decimal]],
    *,
    now: datetime,
    cache_path: Path = DEFAULT_T10YIE_CACHE_PATH,
    meta_path: Path = DEFAULT_T10YIE_META_PATH,
    source: str = "fred_api",
) -> None:
    def write(handle: TextIO) -> None:
        writer = csv.writer(handle)
        writer.writerow(["observation_date", FRED_T10YIE_SERIES_ID])
        for observed, percent in sorted(pairs, key=itemgetter(0)):
            writer.writerow([observed.isoformat(), str(percent)])

    _atomic_write(cache_path, write)
    _write_meta(meta_path, now=now, source=source, series_id=FRED_T10YIE_SERIES_ID)


def resolve_cache_read_path(
    *,
    cache_path: Path = DEFAULT_T10YIE_CACHE_PATH,
    vendored_path: Path = DEFAULT_T10YIE_VENDORED_PATH,
) -> Path:
    if cache_path.is_file():
        return cache_path
    return vendored_path


def is_cache_stale(
    *,
    now: datetime,
    meta_path: Path = DEFAULT_T10YIE_META_PATH,
    ttl: timedelta = CACHE_TTL,
) -> bool:
    if not meta_path.is_file():
        return True
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return True
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    return now - fetched_at > ttl


resolve_t10yie_read_path = resolve_cache_read_path
is_t10yie_cache_stale = is_cache_stale

DEFAULT_SP500_VENDORED_PATH = _DATA_DIR / "sp500_close.csv"
DEFAULT_SP500_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "sp500_close.csv"
DEFAULT_SP500_META_PATH = DEFAULT_MARKET_CACHE_DIR / "sp500_close.meta.json"

DEFAULT_TREASURY_VENDORED_PATH = _DATA_DIR / "treasury_real_yield.csv"
DEFAULT_TREASURY_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "treasury_real_yield.csv"
DEFAULT_TREASURY_META_PATH = DEFAULT_MARKET_CACHE_DIR / "treasury_real_yield.meta.json"

TREASURY_TENORS = ("5", "7", "10", "20", "30")


def _atomic_write(path: Path, write: Callable[[TextIO], None]) -> None:
    """Write through a sibling temp file so an interrupted write keeps the old file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            write(handle)
        os.replace(temp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            temp_path.unlink()
        raise


def _write_meta(meta_path: Path, *, now: datetime, source: str, series_id: str) -> None:
    def write(handle: TextIO) -> None:
        json.dump(
            {
                "fetched_at": now.isoformat(),
                "source": source,
                "series_id": series_id,
            },
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")

    _atomic_write(meta_path, write)


def write_sp500_cache(
    pairs: list[tuple[date, Decimal]],
    *,
    now: datetime,
    cache_path: Path = DEFAULT_SP500_CACHE_PATH,
    meta_path: Path = DEFAULT_SP500_META_PATH,
    source: str = "eod_api",
) -> None:
    def write(handle: TextIO) -> None:
        writer = csv.writer(handle)
        writer.writerow(["observation_date", "close"])
        for observed, close in sorted(pairs, key=itemgetter(0)):
            writer.writerow([observed.isoformat(), str(close)])

    _atomic_write(cache_path, write)
    _write_meta(meta_path, now=now, source=source, series_id=EOD_SP500_SYMBOL)


def write_treasury_cache(
    rows: list[tuple[date, dict[str, Decimal]]],
    *,
    now: datetime,
    cache_path: Path = DEFAULT_TREASURY_CACHE_PATH,
    meta_path: Path = DEFAULT_TREASURY_META_PATH,
    source: str = "treasury_csv",
) -> None:
    complete_rows = [
        (observed, yields)
        for observed, yields in rows
        if all(tenor in yields for tenor in TREASURY_TENORS)
    ]
    if not complete_rows:
        raise ValueError(
            "treasury cache write requires all five tenors on at least one row"
        )

    def write(handle: TextIO) -> None:
        writer = csv.writer(handle)
        writer.writerow(["observation_date", *TREASURY_TENORS])
        for observed, yields in sorted(complete_rows, key=itemgetter(0)):
            writer.writerow(
                [observed.isoformat(), *(str(yields[t]) for t in TREASURY_TENORS)]
            )

    _atomic_write(cache_path, write)
    _write_meta(meta_path, now=now, source=source, series_id=TREASURY_REAL_YIELD_TYPE)
