from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from simulation.market_data.cache import (
    CACHE_TTL,
    is_t10yie_cache_stale,
    resolve_t10yie_read_path,
    write_t10yie_cache,
)


def test_write_t10yie_cache_uses_vendored_csv_shape(tmp_path: Path) -> None:
    cache_path = tmp_path / "t10yie_daily.csv"
    meta_path = tmp_path / "t10yie_daily.meta.json"
    fetched_at = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    pairs = [(date(2026, 6, 27), Decimal("2.35"))]

    write_t10yie_cache(
        pairs, now=fetched_at, cache_path=cache_path, meta_path=meta_path
    )

    assert (
        cache_path.read_text(encoding="utf-8")
        == "observation_date,T10YIE\n2026-06-27,2.35\n"
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["fetched_at"] == fetched_at.isoformat()
    assert meta["source"] == "fred_api"
    assert meta["series_id"] == "T10YIE"


def test_resolve_t10yie_read_path_prefers_cache_when_present(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.csv"
    vendored_path = tmp_path / "vendored.csv"
    cache_path.write_text("observation_date,T10YIE\n2026-01-01,2.0\n", encoding="utf-8")
    vendored_path.write_text(
        "observation_date,T10YIE\n2025-01-01,1.0\n", encoding="utf-8"
    )

    assert (
        resolve_t10yie_read_path(cache_path=cache_path, vendored_path=vendored_path)
        == cache_path
    )


def test_resolve_t10yie_read_path_falls_back_to_vendored_when_cache_missing(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "cache.csv"
    vendored_path = tmp_path / "vendored.csv"
    vendored_path.write_text(
        "observation_date,T10YIE\n2025-01-01,1.0\n", encoding="utf-8"
    )

    assert (
        resolve_t10yie_read_path(cache_path=cache_path, vendored_path=vendored_path)
        == vendored_path
    )


def test_cache_stale_uses_source_ttl_constant(tmp_path: Path) -> None:
    meta_path = tmp_path / "t10yie_daily.meta.json"
    now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    fresh = now - CACHE_TTL + timedelta(seconds=1)
    meta_path.write_text(
        json.dumps({"fetched_at": fresh.isoformat()}), encoding="utf-8"
    )

    assert is_t10yie_cache_stale(now=now, meta_path=meta_path) is False

    stale = now - CACHE_TTL - timedelta(seconds=1)
    meta_path.write_text(
        json.dumps({"fetched_at": stale.isoformat()}), encoding="utf-8"
    )
    assert is_t10yie_cache_stale(now=now, meta_path=meta_path) is True


def test_write_sp500_cache_shape(tmp_path: Path) -> None:
    from simulation.market_data.cache import write_sp500_cache

    cache_path = tmp_path / "sp500_close.csv"
    meta_path = tmp_path / "sp500_close.meta.json"
    fetched_at = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    observed = date(2026, 6, 27)
    close = Decimal("5762.48")
    pairs = [(observed, close)]

    write_sp500_cache(pairs, now=fetched_at, cache_path=cache_path, meta_path=meta_path)

    assert (
        cache_path.read_text(encoding="utf-8")
        == f"observation_date,close\n{observed.isoformat()},{close}\n"
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["fetched_at"] == fetched_at.isoformat()
    assert meta["source"] == "eod_api"


def test_write_treasury_cache_shape(tmp_path: Path) -> None:
    from simulation.market_data.cache import TREASURY_TENORS, write_treasury_cache

    cache_path = tmp_path / "treasury_real_yield.csv"
    meta_path = tmp_path / "treasury_real_yield.meta.json"
    fetched_at = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    observed = date(2026, 6, 27)
    yield_values = [
        Decimal("0.0185"),
        Decimal("0.0190"),
        Decimal("0.0195"),
        Decimal("0.0205"),
        Decimal("0.0215"),
    ]
    yields: dict[str, Decimal] = dict(zip(TREASURY_TENORS, yield_values, strict=True))
    row = (observed, yields)

    write_treasury_cache(
        [row], now=fetched_at, cache_path=cache_path, meta_path=meta_path
    )

    header = ",".join(["observation_date", *TREASURY_TENORS])
    values = ",".join(str(yields[t]) for t in TREASURY_TENORS)
    assert (
        cache_path.read_text(encoding="utf-8")
        == f"{header}\n{observed.isoformat()},{values}\n"
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["source"] == "treasury_csv"
