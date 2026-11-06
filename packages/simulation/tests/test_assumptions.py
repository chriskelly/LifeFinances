from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.models import InflationConfig, PlanningReturnsConfig
from simulation.market_data.inflation import annual_to_monthly

from simulation import (
    InflationResolved,
    assumptions,
    resolve_assumptions,
    run_simulation,
)

TODAY = date(2026, 1, 1)


def test_resolved_assumptions_match_full_simulation_for_same_plan_and_day() -> None:
    # Both paths read the same cache/vendored files; a concurrent refresh could
    # race the comparison.
    plan = default_plan()
    plan.sampling.num_runs = 25

    expected = run_simulation(plan, today=TODAY).resolved_assumptions
    actual = resolve_assumptions(plan, today=TODAY)

    assert actual == expected


def test_resolve_assumptions_never_refreshes_market_data_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = default_plan()
    captured: dict[str, dict] = {}
    real_inflation = assumptions.resolve_inflation
    real_planning = assumptions.resolve_planning_returns

    def spy_inflation(plan, **kwargs):
        captured["inflation"] = kwargs
        return real_inflation(plan, **kwargs)

    def spy_planning(plan, **kwargs):
        captured["planning"] = kwargs
        return real_planning(plan, **kwargs)

    monkeypatch.setattr(assumptions, "resolve_inflation", spy_inflation)
    monkeypatch.setattr(assumptions, "resolve_planning_returns", spy_planning)

    resolve_assumptions(
        plan,
        today=TODAY,
        fred_api_key="fred-key",
        eod_api_key="eod-key",
    )

    assert captured["inflation"]["allow_refresh"] is False
    assert captured["inflation"]["api_key"] == "fred-key"
    assert captured["planning"]["allow_refresh"] is False
    assert captured["planning"]["eod_api_key"] == "eod-key"


def test_resolve_assumptions_forwards_refresh_and_now(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = default_plan()
    sentinel_now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    captured: dict[str, dict] = {}

    class Stop(Exception):
        pass

    def spy_inflation(plan, **kwargs):
        captured["inflation"] = kwargs
        return InflationResolved(
            annual=0.02,
            monthly=annual_to_monthly(0.02),
            source="manual",
        )

    def spy_planning(plan, **kwargs):
        captured["planning"] = kwargs
        raise Stop

    monkeypatch.setattr(assumptions, "resolve_inflation", spy_inflation)
    monkeypatch.setattr(assumptions, "resolve_planning_returns", spy_planning)

    with pytest.raises(Stop):
        resolve_assumptions(
            plan,
            today=TODAY,
            allow_refresh=True,
            now=sentinel_now,
            fred_api_key="fred-key",
            eod_api_key="eod-key",
        )

    assert captured["inflation"]["allow_refresh"] is True
    assert captured["inflation"]["now"] is sentinel_now
    assert captured["inflation"]["today"] == TODAY
    assert captured["planning"]["allow_refresh"] is True
    assert captured["planning"]["now"] is sentinel_now
    assert captured["planning"]["today"] == TODAY


def test_resolve_assumptions_rejects_non_compounding_inflation() -> None:
    plan = default_plan()
    plan.inflation = InflationConfig(mode="manual", manual_annual_rate=Decimal("-1.5"))

    with pytest.raises(ValueError, match="inflation"):
        resolve_assumptions(plan, today=TODAY)


@pytest.mark.parametrize(
    ("delta", "match"),
    [
        ({"custom_stocks_delta": Decimal("-10")}, "stock"),
        ({"custom_bonds_delta": Decimal("-10")}, "bond"),
    ],
)
def test_resolve_assumptions_rejects_returns_that_cannot_compound(
    delta: dict[str, Decimal], match: str
) -> None:
    plan = default_plan()
    plan.planning_returns = PlanningReturnsConfig(
        preset="custom",
        custom_stocks_base="historical",
        custom_bonds_base="historical",
        **delta,
    )

    with pytest.raises(ValueError, match=match):
        resolve_assumptions(plan, today=TODAY)
