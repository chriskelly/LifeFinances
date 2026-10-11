from __future__ import annotations

import math

import numpy as np
import pytest
from core.defaults import default_plan
from core.models import Plan, SamplingConfig
from simulation.market_data.bootstrap import (
    ReturnPaths,
    adjusted_historical_returns,
    build_index_sequences,
    build_return_paths,
)
from simulation.market_data.presets_data import load_empirical_stats_by_block
from simulation.market_data.returns import load_historical_returns
from simulation.planning_returns import resolve_planning_returns
from simulation.presets import historical_annual_return, shift_correction


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

    adjusted = adjusted_historical_returns(plan, planning=planning)
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


# Whole-series proxy for TPAW's "sampled mean = target" guarantee; valid at the
# default block size (block-60 mean ~= series mean). Non-default block sizes are
# covered by test_adjusted_historical_returns_uses_plan_block_size.
@pytest.mark.parametrize("asset", ["stocks", "bonds"])
def test_adjusted_historical_returns_match_planning_target(asset):
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    planning = resolve_planning_returns(plan)

    adjusted = adjusted_historical_returns(plan, planning=planning)

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

    adjusted = adjusted_historical_returns(plan, planning=planning)

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

    adjusted = adjusted_historical_returns(plan, planning=planning)

    assert adjusted.stocks_log.std(ddof=1) == pytest.approx(
        raw.stocks_log.std(ddof=1) * scale
    )
    assert adjusted.bonds_log.std(ddof=1) == pytest.approx(raw.bonds_log.std(ddof=1))


def test_adjusted_historical_returns_uses_plan_block_size():
    plan = _fixed_returns_plan(stocks=0.05, bonds=0.02)
    plan.sampling = plan.sampling.model_copy(update={"block_size_months": 1})
    planning = resolve_planning_returns(plan)
    raw = load_historical_returns()
    block_mean = load_empirical_stats_by_block("stocks")[1].mean

    adjusted = adjusted_historical_returns(plan, planning=planning)
    expected_log_mean = math.log1p(planning.annual_stocks) / 12.0 - shift_correction(
        unadjusted_annual_non_log_mean=block_mean,
        series_log_mean=float(raw.stocks_log.mean()),
        log_volatility_scale=float(plan.planning_returns.stock_volatility_scale),
    )

    assert adjusted.stocks_log.mean() == pytest.approx(expected_log_mean)
