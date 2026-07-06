#!/usr/bin/env python3
# Manual market-data fetch for suggested inflation, S&P close, and Treasury yields.
#
# Prerequisites:
#   Configure FRED and EOD API keys in the app Settings UI. Keys live in the gitignored
#   SQLite DB (data/data.db by default), not in plan JSON or git. Pass --db-path
#   to use a different database. Treasury needs no key.
#
# Usage:
#   # Warm the gitignored T10YIE cache (30-day lookback) — legacy default
#   uv run python scripts/refresh_market_data.py
#
#   # Warm a single source
#   uv run python scripts/refresh_market_data.py --only sp500
#   uv run python scripts/refresh_market_data.py --only treasury
#
#   # Warm every source
#   uv run python scripts/refresh_market_data.py --all
#
#   # Maintainer: full-series fetch → rewrite committed vendored CSV
#   uv run python scripts/refresh_market_data.py --update-vendored
#   uv run python scripts/refresh_market_data.py --all --update-vendored
#   # Update PROVENANCE.md before committing vendored data changes.
#
# Options:
#   --db-path PATH              SQLite DB with AppSettings (default: data/data.db)
#   --only {t10yie,sp500,treasury}  Warm one source (default: t10yie when neither --only nor --all)
#   --all                       Warm every source
#   --cache-path PATH           T10YIE cache CSV (default: data/market_cache/t10yie_daily.csv)
#   --meta-path PATH            T10YIE cache metadata JSON
#   --vendored-path PATH        T10YIE vendored CSV for --update-vendored
#   --sp500-cache-path PATH     S&P cache CSV (default: data/market_cache/sp500_close.csv)
#   --sp500-meta-path PATH      S&P cache metadata JSON
#   --sp500-vendored-path PATH  S&P vendored CSV for --update-vendored
#   --treasury-cache-path PATH  Treasury cache CSV (default: data/market_cache/treasury_real_yield.csv)
#   --treasury-meta-path PATH   Treasury cache metadata JSON
#   --treasury-vendored-path PATH  Treasury vendored CSV for --update-vendored
#   --update-vendored           Fetch full series and write vendored CSV (maintainer only)
#
# Exit codes:
#   0  Success
#   1  Fetch returned no usable observations
#   2  Required API key not configured in Settings
#
# See AGENTS.md and docs/superpowers/specs/2026-06-28-phase-3a-plus-networked-market-data-design.md §5.
"""Refresh live market-data cache from configured local API keys."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from core.settings_repository import SettingsRepository
from simulation.market_data.cache import (
    DEFAULT_SP500_CACHE_PATH,
    DEFAULT_SP500_META_PATH,
    DEFAULT_SP500_VENDORED_PATH,
    DEFAULT_T10YIE_CACHE_PATH,
    DEFAULT_T10YIE_META_PATH,
    DEFAULT_T10YIE_VENDORED_PATH,
    DEFAULT_TREASURY_CACHE_PATH,
    DEFAULT_TREASURY_META_PATH,
    DEFAULT_TREASURY_VENDORED_PATH,
    write_sp500_cache,
    write_t10yie_cache,
    write_treasury_cache,
)
from simulation.market_data.fetch import (
    LOOKBACK_DAYS,
    EodCloseFetcher,
    TreasuryFetcher,
    eod_gspc_close,
    fred_observations,
    treasury_real_yield_curve,
)
from simulation.market_data.treasury import treasury_rows_with_all_tenors

Fetcher = Callable[..., list[tuple[date, Decimal]]]
SOURCES = ("t10yie", "sp500", "treasury")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=None)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--only", choices=SOURCES, default=None)
    source_group.add_argument("--all", action="store_true", help="warm every source")
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_T10YIE_CACHE_PATH)
    parser.add_argument("--meta-path", type=Path, default=DEFAULT_T10YIE_META_PATH)
    parser.add_argument(
        "--vendored-path", type=Path, default=DEFAULT_T10YIE_VENDORED_PATH
    )
    parser.add_argument(
        "--sp500-cache-path", type=Path, default=DEFAULT_SP500_CACHE_PATH
    )
    parser.add_argument("--sp500-meta-path", type=Path, default=DEFAULT_SP500_META_PATH)
    parser.add_argument(
        "--sp500-vendored-path", type=Path, default=DEFAULT_SP500_VENDORED_PATH
    )
    parser.add_argument(
        "--treasury-cache-path", type=Path, default=DEFAULT_TREASURY_CACHE_PATH
    )
    parser.add_argument(
        "--treasury-meta-path", type=Path, default=DEFAULT_TREASURY_META_PATH
    )
    parser.add_argument(
        "--treasury-vendored-path", type=Path, default=DEFAULT_TREASURY_VENDORED_PATH
    )
    parser.add_argument("--update-vendored", action="store_true")
    return parser


def _warm_t10yie(*, args, settings, now, fetcher) -> int:
    if not settings.fred_api_key:
        print("FRED API key is not configured in Settings.", file=sys.stderr)
        return 2
    observation_start = (
        None if args.update_vendored else now.date() - timedelta(days=LOOKBACK_DAYS)
    )
    pairs = fetcher(api_key=settings.fred_api_key, observation_start=observation_start)
    if not pairs:
        print("FRED returned no usable T10YIE observations.", file=sys.stderr)
        return 1
    if args.update_vendored:
        write_t10yie_cache(
            pairs,
            now=now,
            cache_path=args.vendored_path,
            meta_path=args.vendored_path.with_suffix(".meta.json"),
            source="fred_api_full_series",
        )
        args.vendored_path.with_suffix(".meta.json").unlink(missing_ok=True)
        print(f"Wrote vendored T10YIE CSV to {args.vendored_path}")
        print("Update PROVENANCE.md download date before committing.")
        return 0
    write_t10yie_cache(
        pairs, now=now, cache_path=args.cache_path, meta_path=args.meta_path
    )
    latest_date = max(observed for observed, _ in pairs)
    print(f"Wrote T10YIE cache to {args.cache_path} (latest {latest_date.isoformat()})")
    return 0


def _warm_sp500(*, args, settings, now, fetcher) -> int:
    if not settings.eod_api_key:
        print("EOD API key is not configured in Settings.", file=sys.stderr)
        return 2
    from_date = (
        date(1990, 1, 1)
        if args.update_vendored
        else now.date() - timedelta(days=LOOKBACK_DAYS)
    )
    pairs = fetcher(api_key=settings.eod_api_key, from_date=from_date)
    if not pairs:
        print("EOD returned no usable S&P rows.", file=sys.stderr)
        return 1
    target = args.sp500_vendored_path if args.update_vendored else args.sp500_cache_path
    meta = (
        target.with_suffix(".meta.json")
        if args.update_vendored
        else args.sp500_meta_path
    )
    write_sp500_cache(pairs, now=now, cache_path=target, meta_path=meta)
    if args.update_vendored:
        meta.unlink(missing_ok=True)
        print("Update PROVENANCE.md download date before committing.")
    print(f"Wrote S&P close to {target}")
    return 0


def _warm_treasury(*, args, now, fetcher) -> int:
    rows = treasury_rows_with_all_tenors(fetcher(year=now.year))
    if not rows:
        print("Treasury returned no usable rows.", file=sys.stderr)
        return 1
    target = (
        args.treasury_vendored_path
        if args.update_vendored
        else args.treasury_cache_path
    )
    meta = (
        target.with_suffix(".meta.json")
        if args.update_vendored
        else args.treasury_meta_path
    )
    write_treasury_cache(rows, now=now, cache_path=target, meta_path=meta)
    if args.update_vendored:
        meta.unlink(missing_ok=True)
        print("Update PROVENANCE.md download date before committing.")
    print(f"Wrote Treasury real yields to {target}")
    return 0


def main(
    argv: list[str] | None = None,
    *,
    fetcher: Fetcher = fred_observations,
    eod_fetcher: EodCloseFetcher = eod_gspc_close,
    treasury_fetcher: TreasuryFetcher = treasury_real_yield_curve,
) -> int:
    args = _parser().parse_args(argv)
    settings = SettingsRepository(db_path=args.db_path).get()
    now = datetime.now(tz=UTC)
    if args.only:
        selected = [args.only]
    elif args.all:
        selected = list(SOURCES)
    else:
        selected = ["t10yie"]

    worst = 0
    if "t10yie" in selected:
        worst = max(
            worst, _warm_t10yie(args=args, settings=settings, now=now, fetcher=fetcher)
        )
    if "sp500" in selected:
        worst = max(
            worst,
            _warm_sp500(args=args, settings=settings, now=now, fetcher=eod_fetcher),
        )
    if "treasury" in selected:
        worst = max(worst, _warm_treasury(args=args, now=now, fetcher=treasury_fetcher))
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
