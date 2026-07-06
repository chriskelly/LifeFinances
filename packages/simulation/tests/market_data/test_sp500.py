from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from simulation.market_data.sp500 import resolve_latest_sp500_close


def _write_sp500(path: Path, rows: list[tuple[date, float]]) -> Path:
    lines = [f"{observed.isoformat()},{close}" for observed, close in rows]
    path.write_text(
        "\n".join(["observation_date,close", *lines]) + "\n", encoding="utf-8"
    )
    return path


def test_resolves_latest_close_at_or_before_today(tmp_path: Path) -> None:
    earlier = date(2026, 1, 1)
    earlier_close = 5000.0
    later = date(2026, 2, 1)
    later_close = 5100.0
    today = date(2026, 1, 15)
    vendored = _write_sp500(
        tmp_path / "v.csv",
        [(earlier, earlier_close), (later, later_close)],
    )

    resolved = resolve_latest_sp500_close(today=today, vendored_path=vendored)

    assert resolved.close == pytest.approx(earlier_close)
    assert resolved.observation_date == earlier
    assert resolved.source == "vendored"


def test_reports_cache_source_when_cache_present(tmp_path: Path) -> None:
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), 5000.0)])
    cache_path = tmp_path / "cache.csv"
    cache_path.write_text(vendored.read_text(encoding="utf-8"), encoding="utf-8")

    resolved = resolve_latest_sp500_close(
        today=date(2026, 1, 2),
        vendored_path=vendored,
        cache_path=cache_path,
    )

    assert resolved.source == "cache"


def test_reports_live_source_after_refresh(tmp_path: Path) -> None:
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), 5000.0)])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"
    live_observed = date(2026, 1, 3)
    live_close = Decimal("5200.0")

    def fetcher(**kwargs):
        return [(live_observed, live_close)]

    resolved = resolve_latest_sp500_close(
        today=date(2026, 1, 4),
        vendored_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        api_key="eod-key",
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.source == "live"


def test_does_not_call_fetcher_when_not_allowed(tmp_path: Path) -> None:
    vendored_close = 5000.0
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), vendored_close)])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_latest_sp500_close(
        today=date(2026, 1, 2),
        vendored_path=vendored,
        allow_refresh=False,
        api_key="eod-key",
        fetcher=fetcher,
    )

    assert calls == 0


def test_does_not_call_fetcher_without_api_key(tmp_path: Path) -> None:
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), 5000.0)])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_latest_sp500_close(
        today=date(2026, 1, 2),
        vendored_path=vendored,
        allow_refresh=True,
        api_key=None,
        fetcher=fetcher,
    )

    assert calls == 0


def test_refresh_writes_cache_and_uses_live_value_when_stale(tmp_path: Path) -> None:
    vendored_close = 5000.0
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), vendored_close)])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"
    live_observed = date(2026, 1, 3)
    live_close = Decimal("5200.0")
    today = date(2026, 1, 4)
    refresh_now = datetime(2026, 1, 4, 12, tzinfo=UTC)

    def fetcher(**kwargs):
        return [(live_observed, live_close)]

    resolved = resolve_latest_sp500_close(
        today=today,
        vendored_path=vendored,
        allow_refresh=True,
        now=refresh_now,
        api_key="eod-key",
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.close == pytest.approx(float(live_close))
    assert cache_path.is_file()


def test_refresh_failure_falls_back_to_vendored(tmp_path: Path) -> None:
    vendored_close = 5000.0
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), vendored_close)])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"

    def fetcher(**kwargs):
        raise RuntimeError("network unavailable")

    resolved = resolve_latest_sp500_close(
        today=date(2026, 1, 4),
        vendored_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        api_key="eod-key",
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.close == pytest.approx(vendored_close)


def test_vendored_snapshot_resolves_latest_committed_row() -> None:
    import csv

    from simulation.market_data.cache import DEFAULT_SP500_VENDORED_PATH

    today = date(2026, 6, 30)
    with DEFAULT_SP500_VENDORED_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    expected_row = max(rows, key=lambda row: row["observation_date"])
    expected_close = float(expected_row["close"])
    expected_date = date.fromisoformat(expected_row["observation_date"])

    resolved = resolve_latest_sp500_close(today=today)

    assert resolved.close == pytest.approx(expected_close)
    assert resolved.observation_date == expected_date
