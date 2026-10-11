from __future__ import annotations

import dataclasses
from datetime import date
from typing import TYPE_CHECKING

import numpy as np
from core.models import Plan
from pydantic import BaseModel, ConfigDict

from simulation.market_data.presets_data import load_empirical_stats_by_block
from simulation.market_data.returns import HistoricalReturns, load_historical_returns
from simulation.presets import adjust_log_returns

if TYPE_CHECKING:
    from simulation.planning_returns import PlanningReturns


class ReturnPaths(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    stocks_log: np.ndarray
    bonds_log: np.ndarray
    seed: int
    block_size: int
    num_runs: int
    months_per_run: int

    def stocks_log_to_simple(self) -> np.ndarray:
        return np.expm1(self.stocks_log)

    def bonds_log_to_simple(self) -> np.ndarray:
        return np.expm1(self.bonds_log)


def build_index_sequences(
    *,
    seed: int,
    num_runs: int,
    months_per_run: int,
    block_size: int,
    length: int,
    stagger_run_starts: bool,
) -> np.ndarray:
    # Two-level seeding mirrors tpaw: a parent RNG produces a per-run seed, then
    # each run draws its own block-start months. Algorithmic parity, our own
    # determinism (not bit-identical to tpaw's ChaCha8 streams).
    parent = np.random.default_rng(seed)
    run_seeds = parent.integers(0, np.iinfo(np.int64).max, size=num_runs)

    # One extra block for the remainder, one extra for staggering.
    num_blocks = months_per_run // block_size + 2
    month_offsets = np.arange(months_per_run)

    sequences = np.empty((num_runs, months_per_run), dtype=np.int64)
    for run_index in range(num_runs):
        run_rng = np.random.default_rng(int(run_seeds[run_index]))
        block_starts = run_rng.integers(0, length, size=num_blocks)
        stagger = run_index % block_size if stagger_run_starts else 0
        staggered = month_offsets + stagger
        block_index = staggered // block_size
        sequences[run_index] = (
            block_starts[block_index] + staggered % block_size
        ) % length
    return sequences


def adjusted_historical_returns(
    plan: Plan, *, planning: PlanningReturns
) -> HistoricalReturns:
    # TPAW rescales the vendored history so its expected annual non-log return
    # equals the planning (expected) return before any Monte Carlo indexing. The
    # shift correction uses the per-block table mean (not the series mean), and
    # stocks' spread is scaled by the plan's log-volatility scale; bonds use 1.0.
    hist = load_historical_returns()
    block_size = plan.sampling.block_size_months
    scale = float(plan.planning_returns.stock_volatility_scale)
    adjusted_stocks = adjust_log_returns(
        log_returns=hist.stocks_log,
        target_annual_non_log=planning.annual_stocks,
        unadjusted_annual_non_log_mean=load_empirical_stats_by_block("stocks")[
            block_size
        ].mean,
        log_volatility_scale=scale,
    )
    adjusted_bonds = adjust_log_returns(
        log_returns=hist.bonds_log,
        target_annual_non_log=planning.annual_bonds,
        unadjusted_annual_non_log_mean=load_empirical_stats_by_block("bonds")[
            block_size
        ].mean,
        log_volatility_scale=1.0,
    )
    return dataclasses.replace(
        hist, stocks_log=adjusted_stocks, bonds_log=adjusted_bonds
    )


def build_return_paths(
    plan: Plan,
    *,
    planning: PlanningReturns,
    months_per_run: int,
    today: date | None = None,
) -> ReturnPaths:
    _ = today  # reserved: per-run inflation/return paths may key off today later
    hist = adjusted_historical_returns(plan, planning=planning)
    sampling = plan.sampling
    sequences = build_index_sequences(
        seed=sampling.seed,
        num_runs=sampling.num_runs,
        months_per_run=months_per_run,
        block_size=sampling.block_size_months,
        length=hist.length,
        stagger_run_starts=sampling.stagger_run_starts,
    )
    return ReturnPaths(
        stocks_log=hist.stocks_log[sequences],
        bonds_log=hist.bonds_log[sequences],
        seed=sampling.seed,
        block_size=sampling.block_size_months,
        num_runs=sampling.num_runs,
        months_per_run=months_per_run,
    )
