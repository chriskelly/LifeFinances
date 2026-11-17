from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest
from core.models import DEFAULT_PERCENTILES
from simulation.diagnostics import empty_diagnostics
from simulation.result import ResolvedAssumptions, SimulationResult

from web import spending_summary as spending


def _resolved_assumptions() -> ResolvedAssumptions:
    return ResolvedAssumptions(
        annual_inflation=0.02,
        annual_stock_return=0.05,
        annual_bond_return=0.02,
        annual_stock_log_variance=0.03,
        planning_preset="fixed",
        inflation_source="manual",
    )


def _result(
    matrix: np.ndarray,
    *,
    percentiles: list[int] | None = None,
    initial: float = 4_200.0,
) -> SimulationResult:
    horizon = matrix.shape[1]
    resolved_percentiles = percentiles or list(DEFAULT_PERCENTILES)
    totals = np.zeros((len(resolved_percentiles), horizon), dtype=np.float64)
    if horizon:
        totals[0, 0] = initial
    months = np.zeros(horizon, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon,
        num_runs=matrix.shape[0],
        percentiles=resolved_percentiles,
        start_month=(2026, 1),
        balance_start=totals.copy(),
        withdrawals_essential=totals.copy(),
        withdrawals_discretionary=totals.copy(),
        withdrawals_general=totals.copy(),
        withdrawals_total=totals,
        withdrawals_total_by_run=matrix.astype(np.float64),
        savings_stock_allocation=totals.copy(),
        wealth_job=months.copy(),
        wealth_social_security=months.copy(),
        wealth_pension=months.copy(),
        wealth_manual=months.copy(),
        num_runs_insufficient=0,
        diagnostics=empty_diagnostics(months=horizon),
        resolved_assumptions=_resolved_assumptions(),
    )


def test_empty_horizon_has_no_metrics() -> None:
    summary = spending.build(result=_result(np.zeros((10, 0))), threshold=None)

    assert summary.current == spending.SpendingMetrics(None, None, None, None, None)


def test_initial_spending_comes_from_total_spending_month_zero() -> None:
    matrix = np.zeros((2, 12), dtype=np.float64)
    initial = 4_200.0

    summary = spending.build(result=_result(matrix, initial=initial))

    assert summary.current.initial == initial


def test_fewer_than_twelve_months_keeps_initial_and_month_share() -> None:
    matrix = np.array(
        [
            [100.0, 100.0, 100.0],
            [2_000.0, 2_000.0, 2_000.0],
        ]
    )

    summary = spending.build(result=_result(matrix), threshold=Decimal("1000"))

    assert summary.current.initial == 4_200.0
    assert summary.current.lowest_percentile_year is None
    assert summary.current.median_final_year is None
    assert summary.current.bad_year_share is None
    assert summary.current.bad_month_share == pytest.approx(0.5)


def test_lowest_percentile_year_uses_the_lowest_configured_percentile() -> None:
    run_values = np.arange(10, dtype=np.float64).reshape(10, 1)
    matrix = np.tile(run_values, (1, 12))

    summary = spending.build(
        result=_result(matrix, percentiles=[25, 95]), threshold=None
    )

    # np.percentile([0..9], 25) == 2.25; a hardcoded 50th would give 4.5.
    assert summary.current.lowest_percentile_year == pytest.approx(2.25)


def test_median_final_year_uses_the_final_full_window() -> None:
    row = [1_200.0] * 11 + [0.0, 0.0]
    matrix = np.tile(np.array(row, dtype=np.float64), (3, 1))

    summary = spending.build(result=_result(matrix), threshold=None)

    # Window 0 (months 0..11) averages 1100; the final window (1..12) averages 1000.
    assert summary.current.median_final_year == pytest.approx(1_000.0)


def test_bad_year_share_counts_runs_whose_worst_year_is_below_threshold() -> None:
    matrix = np.array(
        [
            [500.0] * 12,
            [900.0] * 12,
            [1_100.0] * 12,
            [1_500.0] * 12,
        ]
    )

    summary = spending.build(result=_result(matrix), threshold=Decimal("1000"))

    assert summary.current.bad_year_share == pytest.approx(0.5)


def test_bad_month_share_counts_every_run_month_below_threshold() -> None:
    run_zero = [100.0] * 6 + [2_000.0] * 6
    run_one = [2_000.0] * 12
    matrix = np.array([run_zero, run_one], dtype=np.float64)

    summary = spending.build(result=_result(matrix), threshold=Decimal("1000"))

    assert summary.current.bad_month_share == pytest.approx(0.25)
    assert summary.current.bad_year_share == pytest.approx(0.0)


def test_unset_threshold_leaves_shares_none() -> None:
    matrix = np.full((2, 12), 1_000.0, dtype=np.float64)

    summary = spending.build(result=_result(matrix), threshold=None)

    assert summary.current.lowest_percentile_year == pytest.approx(1_000.0)
    assert summary.current.median_final_year == pytest.approx(1_000.0)
    assert summary.current.bad_year_share is None
    assert summary.current.bad_month_share is None


def test_zero_threshold_reports_zero_shares() -> None:
    matrix = np.full((2, 12), 100.0, dtype=np.float64)

    summary = spending.build(result=_result(matrix), threshold=Decimal(0))

    assert summary.threshold == Decimal(0)
    assert summary.current.bad_year_share == 0.0
    assert summary.current.bad_month_share == 0.0


def test_previous_metrics_use_the_current_threshold() -> None:
    current = _result(np.full((2, 12), 2_000.0, dtype=np.float64))
    previous = _result(np.full((2, 12), 500.0, dtype=np.float64))

    summary = spending.build(
        result=current, previous=previous, threshold=Decimal("1000")
    )

    assert summary.previous is not None
    assert summary.previous.bad_year_share == pytest.approx(1.0)
    assert summary.current.bad_year_share == pytest.approx(0.0)


def test_build_without_previous_has_no_previous_or_deltas() -> None:
    matrix = np.full((2, 12), 1_000.0, dtype=np.float64)

    summary = spending.build(result=_result(matrix), previous=None)

    assert summary.previous is None
    assert summary.deltas == spending.SpendingDeltas(None, None, None, None, None)


def _metrics(
    *,
    initial: float | None,
    lowest_percentile_year: float | None,
    median_final_year: float | None,
    bad_year_share: float | None,
    bad_month_share: float | None,
) -> spending.SpendingMetrics:
    return spending.SpendingMetrics(
        initial=initial,
        lowest_percentile_year=lowest_percentile_year,
        median_final_year=median_final_year,
        bad_year_share=bad_year_share,
        bad_month_share=bad_month_share,
    )


def test_deltas_are_all_none_without_previous() -> None:
    current = _metrics(
        initial=1_200.0,
        lowest_percentile_year=1_000.0,
        median_final_year=1_100.0,
        bad_year_share=0.25,
        bad_month_share=0.5,
    )

    deltas = spending.deltas_for(current=current, previous=None)

    assert deltas == spending.SpendingDeltas(None, None, None, None, None)


def test_deltas_subtract_previous_from_current() -> None:
    current = _metrics(
        initial=1_200.0,
        lowest_percentile_year=1_000.0,
        median_final_year=1_100.0,
        bad_year_share=0.25,
        bad_month_share=0.5,
    )
    previous = _metrics(
        initial=1_000.0,
        lowest_percentile_year=900.0,
        median_final_year=1_200.0,
        bad_year_share=0.5,
        bad_month_share=0.4,
    )

    deltas = spending.deltas_for(current=current, previous=previous)

    assert deltas.initial == pytest.approx(200.0)
    assert deltas.lowest_percentile_year == pytest.approx(100.0)
    assert deltas.median_final_year == pytest.approx(-100.0)
    assert deltas.bad_year_share == pytest.approx(-0.25)
    assert deltas.bad_month_share == pytest.approx(0.1)


def test_deltas_skip_metrics_missing_from_either_snapshot() -> None:
    current = _metrics(
        initial=1_200.0,
        lowest_percentile_year=1_000.0,
        median_final_year=1_100.0,
        bad_year_share=0.25,
        bad_month_share=0.5,
    )
    previous = _metrics(
        initial=1_000.0,
        lowest_percentile_year=None,
        median_final_year=None,
        bad_year_share=None,
        bad_month_share=0.4,
    )

    deltas = spending.deltas_for(current=current, previous=previous)

    assert deltas.initial == pytest.approx(200.0)
    assert deltas.lowest_percentile_year is None
    assert deltas.median_final_year is None
    assert deltas.bad_year_share is None
    assert deltas.bad_month_share == pytest.approx(0.1)


def test_spending_increase_is_better() -> None:
    marker = spending.delta_marker(value=100.0, kind="usd", higher_is_better=True)

    assert marker == spending.DeltaMarker("▲", "+$100/mo", "better")


def test_spending_decrease_is_worse() -> None:
    marker = spending.delta_marker(value=-100.0, kind="usd", higher_is_better=True)

    assert marker == spending.DeltaMarker("▼", "-$100/mo", "worse")


def test_share_decrease_is_better() -> None:
    marker = spending.delta_marker(value=-0.031, kind="pp", higher_is_better=False)

    assert marker == spending.DeltaMarker("▼", "-3.1 pp", "better")


def test_share_increase_is_worse() -> None:
    marker = spending.delta_marker(value=0.031, kind="pp", higher_is_better=False)

    assert marker == spending.DeltaMarker("▲", "+3.1 pp", "worse")


def test_zero_or_missing_delta_has_no_marker() -> None:
    assert spending.delta_marker(value=None, kind="usd", higher_is_better=True) is None
    assert spending.delta_marker(value=0.0, kind="usd", higher_is_better=True) is None


def test_a_delta_that_rounds_to_zero_has_no_marker() -> None:
    assert spending.delta_marker(value=0.4, kind="usd", higher_is_better=True) is None
    assert (
        spending.delta_marker(value=0.000000004, kind="pp", higher_is_better=False)
        is None
    )
