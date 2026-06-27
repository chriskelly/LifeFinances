from __future__ import annotations

from datetime import date
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
