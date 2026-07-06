from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from simulation.market_data.cache import TREASURY_TENORS
from simulation.market_data.treasury import resolve_treasury_real_yields


def _write_treasury(path: Path, rows: list[tuple[date, dict[str, float]]]) -> Path:
    lines = []
    for observed, yields in rows:
        values = ",".join(str(yields[t]) for t in TREASURY_TENORS)
        lines.append(f"{observed.isoformat()},{values}")
    header = ",".join(["observation_date", *TREASURY_TENORS])
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    return path


def test_resolves_latest_curve_at_or_before_today(tmp_path: Path) -> None:
    earlier = date(2026, 1, 1)
    earlier_twenty_yr = 0.021
    later = date(2026, 2, 1)
    today = date(2026, 1, 15)
    vendored = _write_treasury(
        tmp_path / "v.csv",
        [
            (earlier, {t: earlier_twenty_yr for t in TREASURY_TENORS}),
            (later, {t: 0.019 for t in TREASURY_TENORS}),
        ],
    )

    resolved = resolve_treasury_real_yields(today=today, vendored_path=vendored)

    assert resolved.yields["20"] == pytest.approx(earlier_twenty_yr)
    assert resolved.observation_date == earlier


def test_does_not_call_fetcher_when_not_allowed(tmp_path: Path) -> None:
    vendored = _write_treasury(
        tmp_path / "v.csv", [(date(2026, 1, 1), {t: 0.02 for t in TREASURY_TENORS})]
    )
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_treasury_real_yields(
        today=date(2026, 1, 2),
        vendored_path=vendored,
        allow_refresh=False,
        fetcher=fetcher,
    )

    assert calls == 0


def test_refresh_writes_cache_and_uses_live_value_when_stale(tmp_path: Path) -> None:
    vendored = _write_treasury(
        tmp_path / "v.csv", [(date(2026, 1, 1), {t: 0.02 for t in TREASURY_TENORS})]
    )
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"
    live_observed = date(2026, 1, 3)
    live_twenty_yr = Decimal("0.013")
    today = date(2026, 1, 4)
    refresh_now = datetime(2026, 1, 4, 12, tzinfo=UTC)

    def fetcher(**kwargs):
        return [
            (
                live_observed,
                {t: live_twenty_yr for t in TREASURY_TENORS},
            )
        ]

    resolved = resolve_treasury_real_yields(
        today=today,
        vendored_path=vendored,
        allow_refresh=True,
        now=refresh_now,
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.yields["20"] == pytest.approx(float(live_twenty_yr))
    assert cache_path.is_file()


def test_refresh_failure_falls_back_to_vendored(tmp_path: Path) -> None:
    vendored_twenty_yr = 0.021
    vendored = _write_treasury(
        tmp_path / "v.csv",
        [(date(2026, 1, 1), {t: vendored_twenty_yr for t in TREASURY_TENORS})],
    )
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"

    def fetcher(**kwargs):
        raise RuntimeError("network unavailable")

    resolved = resolve_treasury_real_yields(
        today=date(2026, 1, 4),
        vendored_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.yields["20"] == pytest.approx(vendored_twenty_yr)


def test_skips_incomplete_curve_row_when_newer(tmp_path: Path) -> None:
    complete_date = date(2026, 1, 1)
    complete_twenty_yr = 0.021
    incomplete_date = date(2026, 2, 1)
    today = date(2026, 2, 15)
    header = ",".join(["observation_date", *TREASURY_TENORS])
    complete_values = ",".join(str(complete_twenty_yr) for _ in TREASURY_TENORS)
    incomplete_values = ",".join(["0.0185", "0.0190", "0.0195", "0.0205", ""])
    vendored = tmp_path / "v.csv"
    vendored.write_text(
        "\n".join(
            [
                header,
                f"{complete_date.isoformat()},{complete_values}",
                f"{incomplete_date.isoformat()},{incomplete_values}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    resolved = resolve_treasury_real_yields(today=today, vendored_path=vendored)

    assert resolved.observation_date == complete_date
    assert resolved.yields["20"] == pytest.approx(complete_twenty_yr)
    assert set(resolved.yields) == set(TREASURY_TENORS)


def test_vendored_snapshot_resolves_latest_committed_curve() -> None:
    import csv

    from simulation.market_data.cache import (
        DEFAULT_TREASURY_VENDORED_PATH,
        TREASURY_TENORS,
    )

    today = date(2026, 6, 30)
    with DEFAULT_TREASURY_VENDORED_PATH.open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        rows = list(csv.DictReader(handle))
    expected_row = max(rows, key=lambda row: row["observation_date"])
    expected_twenty_yr = float(expected_row["20"])
    expected_date = date.fromisoformat(expected_row["observation_date"])

    resolved = resolve_treasury_real_yields(today=today)

    assert resolved.yields["20"] == pytest.approx(expected_twenty_yr)
    assert resolved.observation_date == expected_date
    assert set(resolved.yields) == set(TREASURY_TENORS)
