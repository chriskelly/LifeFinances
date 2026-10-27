from __future__ import annotations

import dataclasses
import math
from decimal import Decimal

import numpy as np
import pytest
from core.defaults import default_plan
from core.models import DEFAULT_BLOCK_SIZE_MONTHS, Plan, SamplingConfig
from simulation.market_data.bootstrap import (
    ReturnPaths,
    adjusted_historical_returns,
    build_index_sequences,
    build_return_paths,
)
from simulation.market_data.presets_data import empirical_stats
from simulation.market_data.returns import load_historical_returns
from simulation.planning_returns import resolve_planning_returns
from simulation.presets import (
    adjust_log_returns,
    historical_annual_return,
    shift_correction,
)


def _fixed_returns_plan(*, stocks: float, bonds: float) -> Plan:
    plan = default_plan()
    plan.planning_returns = plan.planning_returns.model_copy(
        update={
            "preset": "fixed",
            "expected_annual_return_stocks": stocks,
            "expected_annual_return_bonds": bonds,
        }
    )
    return plan


def _sequences(
    *,
    seed: int,
    num_runs: int,
    months: int,
    block_size: int,
    length: int,
    stagger: bool = True,
) -> np.ndarray:
    return build_index_sequences(
        seed=seed,
        num_runs=num_runs,
        months_per_run=months,
        block_size=block_size,
        length=length,
        stagger_run_starts=stagger,
    )


def test_sequence_shape_matches_runs_and_months() -> None:
    num_runs, months = 7, 40

    seqs = _sequences(
        seed=1, num_runs=num_runs, months=months, block_size=12, length=600
    )

    assert seqs.shape == (num_runs, months)


def test_same_seed_is_deterministic() -> None:
    a = _sequences(seed=42, num_runs=5, months=30, block_size=12, length=600)
    b = _sequences(seed=42, num_runs=5, months=30, block_size=12, length=600)

    assert np.array_equal(a, b)


def test_different_seed_changes_sequences() -> None:
    a = _sequences(seed=1, num_runs=5, months=30, block_size=12, length=600)
    b = _sequences(seed=2, num_runs=5, months=30, block_size=12, length=600)

    assert not np.array_equal(a, b)


def test_all_indices_are_within_series_bounds() -> None:
    length = 600

    seqs = _sequences(seed=3, num_runs=10, months=120, block_size=60, length=length)

    assert seqs.min() >= 0
    assert seqs.max() < length


def test_within_block_indices_are_consecutive_mod_length() -> None:
    length = 600
    block_size = 12
    # No staggering so block 0 spans months [0, block_size).
    seqs = _sequences(
        seed=4,
        num_runs=1,
        months=block_size,
        block_size=block_size,
        length=length,
        stagger=False,
    )

    run = seqs[0]
    steps = (run[1:] - run[:-1]) % length
    assert np.all(steps == 1)


def test_staggering_offsets_block_boundary_across_runs() -> None:
    length = 600
    block_size = 12
    # With stagger, run_index r starts at offset r % block_size into its first block,
    # so the first block boundary (where index jumps) shifts by run.
    seqs = _sequences(
        seed=5,
        num_runs=2,
        months=block_size * 2,
        block_size=block_size,
        length=length,
        stagger=True,
    )

    def first_break(run: np.ndarray) -> int:
        steps = (run[1:] - run[:-1]) % length
        return int(np.argmax(steps != 1))

    assert first_break(seqs[0]) != first_break(seqs[1])


def test_build_return_paths_gathers_both_assets_with_metadata() -> None:
    plan = default_plan()
    plan.sampling = SamplingConfig(num_runs=8, block_size_months=24, seed=99)
    months = 36
    planning = resolve_planning_returns(plan)

    paths = build_return_paths(plan, planning=planning, months_per_run=months)

    adjusted = adjusted_historical_returns(planning=planning)
    assert isinstance(paths, ReturnPaths)
    assert paths.stocks_log.shape == (plan.sampling.num_runs, months)
    assert paths.bonds_log.shape == (plan.sampling.num_runs, months)
    assert paths.num_runs == plan.sampling.num_runs
    assert paths.months_per_run == months
    assert paths.block_size == plan.sampling.block_size_months
    assert paths.seed == plan.sampling.seed
    # Every sampled value is a member of the adjusted log series.
    assert np.isin(paths.stocks_log, adjusted.stocks_log).all()


def test_build_return_paths_is_deterministic_under_same_seed() -> None:
    plan = default_plan()
    plan.sampling = SamplingConfig(num_runs=4, block_size_months=24, seed=7)
    planning = resolve_planning_returns(plan)

    a = build_return_paths(plan, planning=planning, months_per_run=24)
    b = build_return_paths(plan, planning=planning, months_per_run=24)

    assert np.array_equal(a.stocks_log, b.stocks_log)
    assert np.array_equal(a.bonds_log, b.bonds_log)


def test_build_return_paths_matches_the_plan_derived_computation() -> None:
    # The pre-change computation read block size and scale from the plan and the
    # targets from planning. For a matched pair the output must stay identical to
    # that path. Compared in-process rather than against a pinned hash: platform
    # float means can differ in the last bits, so a stored digest is not portable.
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    planning = resolve_planning_returns(plan)
    months_per_run = 24
    raw = load_historical_returns()
    block_size = plan.sampling.block_size_months

    stocks_log = adjust_log_returns(
        log_returns=raw.stocks_log,
        target_annual_non_log=planning.annual_stocks,
        unadjusted_annual_non_log_mean=empirical_stats(
            asset="stocks", block_size=block_size
        ).annual_non_log_mean,
        log_volatility_scale=float(plan.planning_returns.stock_volatility_scale),
    )
    bonds_log = adjust_log_returns(
        log_returns=raw.bonds_log,
        target_annual_non_log=planning.annual_bonds,
        unadjusted_annual_non_log_mean=empirical_stats(
            asset="bonds", block_size=block_size
        ).annual_non_log_mean,
        log_volatility_scale=1.0,
    )
    sequences = build_index_sequences(
        seed=plan.sampling.seed,
        num_runs=plan.sampling.num_runs,
        months_per_run=months_per_run,
        block_size=block_size,
        length=raw.length,
        stagger_run_starts=plan.sampling.stagger_run_starts,
    )

    paths = build_return_paths(plan, planning=planning, months_per_run=months_per_run)

    assert np.array_equal(paths.stocks_log, stocks_log[sequences])
    assert np.array_equal(paths.bonds_log, bonds_log[sequences])


# Whole-series proxy for TPAW's "sampled mean = target" guarantee; valid at the
# default block size (block-60 mean ~= series mean). Non-default block sizes are
# covered by test_adjusted_historical_returns_uses_resolved_block_size.
@pytest.mark.parametrize("asset", ["stocks", "bonds"])
def test_adjusted_historical_returns_match_planning_target(asset):
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    planning = resolve_planning_returns(plan)

    adjusted = adjusted_historical_returns(planning=planning)

    target = planning.annual_stocks if asset == "stocks" else planning.annual_bonds
    series = adjusted.stocks_log if asset == "stocks" else adjusted.bonds_log
    assert historical_annual_return(series) == pytest.approx(target, abs=2e-3)


def test_adjusted_historical_returns_historical_preset_is_approximately_unchanged():
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    plan.planning_returns = plan.planning_returns.model_copy(
        update={"preset": "historical"}
    )
    planning = resolve_planning_returns(plan)
    raw = load_historical_returns()

    adjusted = adjusted_historical_returns(planning=planning)

    assert historical_annual_return(adjusted.stocks_log) == pytest.approx(
        historical_annual_return(raw.stocks_log), abs=1e-3
    )


def test_adjusted_historical_returns_scales_only_stocks_spread_by_stock_volatility_scale():
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    scale = 0.5
    plan.planning_returns = plan.planning_returns.model_copy(
        update={"stock_volatility_scale": scale}
    )
    planning = resolve_planning_returns(plan)
    raw = load_historical_returns()

    adjusted = adjusted_historical_returns(planning=planning)

    assert adjusted.stocks_log.std(ddof=1) == pytest.approx(
        raw.stocks_log.std(ddof=1) * scale
    )
    assert adjusted.bonds_log.std(ddof=1) == pytest.approx(raw.bonds_log.std(ddof=1))


@pytest.mark.parametrize("asset", ["stocks", "bonds"])
def test_adjusted_historical_returns_uses_resolved_block_size(asset):
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    plan.sampling = plan.sampling.model_copy(update={"block_size_months": 1})
    planning = resolve_planning_returns(plan)
    raw = load_historical_returns()

    adjusted = adjusted_historical_returns(planning=planning)

    target = planning.annual_stocks if asset == "stocks" else planning.annual_bonds
    raw_log = raw.stocks_log if asset == "stocks" else raw.bonds_log
    adjusted_log = adjusted.stocks_log if asset == "stocks" else adjusted.bonds_log
    scale = planning.stock_volatility_scale if asset == "stocks" else 1.0
    expected_log_mean = math.log1p(target) / 12.0 - shift_correction(
        unadjusted_annual_non_log_mean=empirical_stats(
            asset=asset, block_size=planning.block_size_months
        ).annual_non_log_mean,
        series_log_mean=float(raw_log.mean()),
        log_volatility_scale=scale,
    )

    assert adjusted_log.mean() == pytest.approx(expected_log_mean)


# TPAW's adjust_log_returns_monte_carlo asserts the target on the series the
# Monte Carlo actually indexes. Many runs over a long horizon pin the sampled
# annual non-log mean; abs=5e-3 is ~10% of the 5% stock target and well below
# the 3% stocks/bonds gap, so a wrong target or a swapped asset fails.
@pytest.mark.parametrize("asset", ["stocks", "bonds"])
def test_sampled_return_paths_match_planning_target(asset):
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    plan.sampling = SamplingConfig(num_runs=1000, block_size_months=60, seed=7)
    planning = resolve_planning_returns(plan)

    paths = build_return_paths(plan, planning=planning, months_per_run=600)

    target = planning.annual_stocks if asset == "stocks" else planning.annual_bonds
    sampled = paths.stocks_log if asset == "stocks" else paths.bonds_log
    assert historical_annual_return(sampled.ravel()) == pytest.approx(target, abs=5e-3)


def test_build_return_paths_rejects_block_size_mismatch():
    # Resolve planning first, then change the plan's sampling: the two inputs now
    # disagree, which used to silently shift the adjustment targets.
    mutated_block_size = 1
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    assert plan.sampling.block_size_months == DEFAULT_BLOCK_SIZE_MONTHS
    planning = resolve_planning_returns(plan)
    plan.sampling = plan.sampling.model_copy(
        update={"block_size_months": mutated_block_size}
    )

    with pytest.raises(ValueError, match="does not match") as excinfo:
        build_return_paths(plan, planning=planning, months_per_run=12)

    message = str(excinfo.value)
    assert f"plan.sampling.block_size_months={mutated_block_size}" in message
    assert f"planning.block_size_months={planning.block_size_months}" in message


def test_build_return_paths_rejects_volatility_scale_mismatch():
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    planning = resolve_planning_returns(plan)
    mutated_scale = Decimal("0.5")
    plan.planning_returns = plan.planning_returns.model_copy(
        update={"stock_volatility_scale": mutated_scale}
    )

    with pytest.raises(ValueError, match="does not match") as excinfo:
        build_return_paths(plan, planning=planning, months_per_run=12)

    message = str(excinfo.value)
    assert (
        f"plan.planning_returns.stock_volatility_scale={float(mutated_scale)}"
        in message
    )
    assert (
        f"planning.stock_volatility_scale={planning.stock_volatility_scale}" in message
    )


@pytest.mark.parametrize("hand_built", [False, True], ids=["resolved", "hand-built"])
def test_build_return_paths_accepts_decimal_scale(hand_built: bool):
    # The editor stores a Decimal scale on the plan; resolution narrows it to a
    # float, and a hand-built PlanningReturns can carry the Decimal directly.
    # Both shapes must pass the guard and reach the adjustment.
    scale = Decimal("0.1")
    months_per_run = 12
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    plan.planning_returns = plan.planning_returns.model_copy(
        update={"stock_volatility_scale": scale}
    )
    planning = resolve_planning_returns(plan)
    if hand_built:
        planning = dataclasses.replace(planning, stock_volatility_scale=scale)

    paths = build_return_paths(plan, planning=planning, months_per_run=months_per_run)

    assert paths.stocks_log.shape == (plan.sampling.num_runs, months_per_run)
