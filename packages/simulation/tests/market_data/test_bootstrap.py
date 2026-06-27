from __future__ import annotations

import numpy as np
from core.defaults import default_plan
from core.models import SamplingConfig
from simulation.market_data.bootstrap import (
    ReturnPaths,
    build_index_sequences,
    build_return_paths,
)
from simulation.market_data.returns import load_historical_returns


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

    paths = build_return_paths(plan, months_per_run=months)

    hist = load_historical_returns()
    assert isinstance(paths, ReturnPaths)
    assert paths.stocks_log.shape == (plan.sampling.num_runs, months)
    assert paths.bonds_log.shape == (plan.sampling.num_runs, months)
    assert paths.num_runs == plan.sampling.num_runs
    assert paths.months_per_run == months
    assert paths.block_size == plan.sampling.block_size_months
    assert paths.seed == plan.sampling.seed
    # Every sampled value is a member of the source log series.
    assert np.isin(paths.stocks_log, hist.stocks_log).all()


def test_build_return_paths_is_deterministic_under_same_seed() -> None:
    plan = default_plan()
    plan.sampling = SamplingConfig(num_runs=4, block_size_months=24, seed=7)

    a = build_return_paths(plan, months_per_run=24)
    b = build_return_paths(plan, months_per_run=24)

    assert np.array_equal(a.stocks_log, b.stocks_log)
    assert np.array_equal(a.bonds_log, b.bonds_log)
