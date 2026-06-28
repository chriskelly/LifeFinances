from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from core.defaults import default_plan
from core.models import InflationConfig
from simulation.market_data.inflation import (
    InflationResolved,
    annual_to_monthly,
    resolve_inflation,
)


def _write_t10yie(path: Path, rows: list[str]) -> Path:
    path.write_text(
        "\n".join(["observation_date,T10YIE", *rows]) + "\n", encoding="utf-8"
    )
    return path


def _suggested_plan():
    plan = default_plan()
    plan.inflation = InflationConfig(mode="suggested")
    return plan


def test_annual_to_monthly_matches_compounding_formula() -> None:
    annual = 0.03

    monthly = annual_to_monthly(annual)

    assert (1 + monthly) ** 12 == pytest.approx(1 + annual)


def test_suggested_uses_latest_observation_at_or_before_today(tmp_path: Path) -> None:
    # second value is after the date used for today, so it's ignored
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.0", "2026-02-01,2.5"])

    resolved = resolve_inflation(
        _suggested_plan(), today=date(2026, 1, 15), t10yie_path=csv
    )

    assert resolved.source == "suggested"
    assert resolved.annual == pytest.approx(0.020)


def test_suggested_picks_exact_match_on_observation_date(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.0", "2026-02-01,2.5"])

    resolved = resolve_inflation(
        _suggested_plan(), today=date(2026, 2, 1), t10yie_path=csv
    )

    assert resolved.annual == pytest.approx(0.025)


def test_suggested_skips_non_numeric_rows(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.0", "2026-02-01,."])

    resolved = resolve_inflation(
        _suggested_plan(), today=date(2026, 2, 15), t10yie_path=csv
    )

    assert resolved.annual == pytest.approx(0.020)


def test_refresh_does_not_call_fetcher_when_not_allowed(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolved = resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 2),
        t10yie_path=csv,
        allow_refresh=False,
        api_key="fred-key",
        fetcher=fetcher,
    )

    assert resolved.annual == pytest.approx(0.020)
    assert calls == 0


def test_refresh_does_not_call_fetcher_without_api_key(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 2),
        t10yie_path=csv,
        allow_refresh=True,
        api_key=None,
        fetcher=fetcher,
    )

    assert calls == 0


def test_refresh_writes_cache_and_uses_live_value_when_stale(tmp_path: Path) -> None:
    vendored = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"
    expected_percent = Decimal("2.50")

    def fetcher(**kwargs):
        return [(date(2026, 1, 3), expected_percent)]

    resolved = resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 4),
        t10yie_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        api_key="fred-key",
        fetcher=fetcher,
        t10yie_cache_path=cache_path,
        t10yie_meta_path=meta_path,
    )

    assert resolved.annual == pytest.approx(0.025)
    assert cache_path.is_file()
    assert meta_path.is_file()


def test_refresh_failure_falls_back_to_vendored(tmp_path: Path) -> None:
    vendored = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"

    def fetcher(**kwargs):
        raise RuntimeError("network unavailable")

    resolved = resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 4),
        t10yie_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        api_key="fred-key",
        fetcher=fetcher,
        t10yie_cache_path=cache_path,
        t10yie_meta_path=meta_path,
    )

    assert resolved.annual == pytest.approx(0.020)


def test_suggested_rounds_to_three_decimal_places(tmp_path: Path) -> None:
    # 2.37% -> 0.0237 -> round half-away to 3 dp -> 0.024
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.37"])

    resolved = resolve_inflation(
        _suggested_plan(), today=date(2026, 1, 2), t10yie_path=csv
    )

    assert resolved.annual == pytest.approx(0.024)


def test_manual_mode_uses_configured_rate(tmp_path: Path) -> None:
    expected_annual = Decimal("0.031")
    plan = default_plan()
    plan.inflation = InflationConfig(mode="manual", manual_annual_rate=expected_annual)

    resolved = resolve_inflation(plan, today=date(2026, 1, 2))

    assert resolved.source == "manual"
    assert resolved.annual == pytest.approx(float(expected_annual))
    assert resolved.monthly == pytest.approx(annual_to_monthly(float(expected_annual)))


def test_resolve_returns_inflation_resolved_type() -> None:
    plan = default_plan()
    plan.inflation = InflationConfig(mode="manual", manual_annual_rate=Decimal("0.02"))

    resolved = resolve_inflation(plan, today=date(2026, 1, 2))

    assert isinstance(resolved, InflationResolved)
