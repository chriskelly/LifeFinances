from datetime import date

import pytest
from core.models import PlanningPreset
from pydantic import ValidationError
from simulation.market_data import (
    InflationResolved,
    SP500Resolved,
    TreasuryYieldsResolved,
)
from simulation.market_data.inflation import annual_to_monthly
from simulation.planning_returns import TWENTY_YEAR_TENOR, PlanningReturns
from simulation.result import ResolvedAssumptions, build_resolved_assumptions


def test_snapshot_uses_exact_resolver_values() -> None:
    annual_inflation = 0.023
    annual_stocks = 0.051
    annual_bonds = 0.018
    annual_variance = 0.031
    preset: PlanningPreset = "fixed"
    inflation_source = "manual"
    inflation = InflationResolved(
        annual=annual_inflation,
        monthly=annual_to_monthly(annual_inflation),
        source=inflation_source,
    )
    planning = PlanningReturns(
        annual_stocks=annual_stocks,
        annual_bonds=annual_bonds,
        annual_stock_log_variance=annual_variance,
    )

    snapshot = build_resolved_assumptions(
        inflation=inflation, planning=planning, preset=preset
    )

    assert snapshot.annual_inflation == annual_inflation
    assert snapshot.annual_stock_return == annual_stocks
    assert snapshot.annual_bond_return == annual_bonds
    assert snapshot.annual_stock_log_variance == annual_variance
    assert snapshot.planning_preset == preset
    assert snapshot.inflation_source == inflation_source


def test_snapshot_carries_only_present_market_provenance() -> None:
    sp500_date = date(2026, 5, 1)
    treasury_date = date(2026, 5, 2)
    sp500 = SP500Resolved(close=6_000.0, observation_date=sp500_date, source="live")
    treasury = TreasuryYieldsResolved(
        yields={TWENTY_YEAR_TENOR: 0.018},
        observation_date=treasury_date,
        source="cache",
    )
    inflation_observation_date = date(2026, 4, 30)
    expected_inflation_source = "vendored"
    inflation = InflationResolved(
        annual=0.023,
        monthly=annual_to_monthly(0.023),
        source="suggested",
        market_source=expected_inflation_source,
        observation_date=inflation_observation_date,
    )
    planning = PlanningReturns(
        annual_stocks=0.051,
        annual_bonds=0.018,
        annual_stock_log_variance=0.031,
        sp500=sp500,
        treasury=treasury,
    )

    snapshot = build_resolved_assumptions(
        inflation=inflation,
        planning=planning,
        preset="regression_prediction",
    )

    assert snapshot.inflation_source == expected_inflation_source
    assert snapshot.inflation_observation_date == inflation_observation_date
    assert snapshot.sp500_source == sp500.source
    assert snapshot.sp500_observation_date == sp500_date
    assert snapshot.treasury_source == treasury.source
    assert snapshot.treasury_observation_date == treasury_date


@pytest.mark.parametrize("feed", ["sp500", "treasury"])
def test_market_provenance_source_requires_observation_date(feed: str) -> None:
    # Display code reads the date whenever the source is set, so a half-set
    # pair must be rejected here rather than raising during template render.
    half_set = {f"{feed}_source": "cache", f"{feed}_observation_date": None}

    with pytest.raises(ValidationError, match=feed):
        ResolvedAssumptions(
            annual_inflation=0.02,
            annual_stock_return=0.05,
            annual_bond_return=0.02,
            annual_stock_log_variance=0.03,
            planning_preset="fixed",
            inflation_source="manual",
            **half_set,
        )
