#!/usr/bin/env python3
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
    DEFAULT_T10YIE_CACHE_PATH,
    DEFAULT_T10YIE_META_PATH,
    DEFAULT_T10YIE_VENDORED_PATH,
    write_t10yie_cache,
)
from simulation.market_data.fetch import LOOKBACK_DAYS, fred_observations

Fetcher = Callable[..., list[tuple[date, Decimal]]]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_T10YIE_CACHE_PATH)
    parser.add_argument("--meta-path", type=Path, default=DEFAULT_T10YIE_META_PATH)
    parser.add_argument(
        "--vendored-path", type=Path, default=DEFAULT_T10YIE_VENDORED_PATH
    )
    parser.add_argument("--update-vendored", action="store_true")
    return parser


def main(argv: list[str] | None = None, *, fetcher: Fetcher = fred_observations) -> int:
    args = _parser().parse_args(argv)
    settings = SettingsRepository(db_path=args.db_path).get()
    if not settings.fred_api_key:
        print("FRED API key is not configured in Settings.", file=sys.stderr)
        return 2

    now = datetime.now(tz=UTC)
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
        pairs,
        now=now,
        cache_path=args.cache_path,
        meta_path=args.meta_path,
    )
    latest_date = max(observed for observed, _ in pairs)
    print(f"Wrote T10YIE cache to {args.cache_path} (latest {latest_date.isoformat()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
