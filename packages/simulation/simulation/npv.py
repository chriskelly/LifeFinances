from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FloatOrArray = float | np.ndarray


def backward_npv_including_current(
    real_series: np.ndarray, *, one_over_1_plus_r: float
) -> np.ndarray:
    """NPV of `real_series[m:]` including month `m`, discounting at a constant rate."""
    months = real_series.shape[0]
    out = np.empty(months, dtype=np.float64)
    running = 0.0
    for month in range(months - 1, -1, -1):
        running = running * one_over_1_plus_r + float(real_series[month])
        out[month] = running
    return out


@dataclass(frozen=True)
class ExpensesScale:
    discretionary: FloatOrArray
    legacy: FloatOrArray


def expenses_scale_for_normal_run(
    *,
    wealth: FloatOrArray,
    scheduled_wealth: float,
    elasticity_discretionary: float,
    elasticity_legacy: float,
) -> ExpensesScale:
    """Scale discretionary/legacy goals by how this run's wealth compares to
    the scheduled (expected-run) wealth. `scheduled_wealth` and the
    elasticities are always per-month scalars; `wealth` may be a scalar (the
    expected run) or a per-run array (normal runs), and the result shape
    follows `wealth`.
    """
    if scheduled_wealth == 0.0:
        p_increase = 0.0
    else:
        p_increase = wealth / scheduled_wealth - 1.0
    return ExpensesScale(
        discretionary=np.maximum(0.0, p_increase * elasticity_discretionary + 1.0),
        legacy=np.maximum(0.0, p_increase * elasticity_legacy + 1.0),
    )


def carve_pools(
    *,
    wealth: FloatOrArray,
    essential_reserve: FloatOrArray,
    discretionary_reserve: FloatOrArray,
    legacy_reserve: FloatOrArray,
) -> tuple[FloatOrArray, FloatOrArray, FloatOrArray]:
    """`AccountForWithdrawal` carve: draw each reserve clamped to the running
    balance (essential -> discretionary -> legacy), returning the constrained
    (discretionary, legacy, general) pools. Works elementwise on floats or
    arrays. Mirrors tpaw's `_NPVSpendingScaledAndConstrainedToWealth`
    construction.
    """
    remaining = np.maximum(0.0, wealth - np.minimum(wealth, essential_reserve))
    discretionary = np.minimum(remaining, discretionary_reserve)
    remaining = np.maximum(0.0, remaining - discretionary)
    legacy = np.minimum(remaining, legacy_reserve)
    general = np.maximum(0.0, remaining - legacy)
    return discretionary, legacy, general


def target_general_withdrawal(
    *,
    general_pool: FloatOrArray,
    cumulative_1_plus_g_over_1_plus_r: float,
    withdrawal_started: bool = True,
) -> FloatOrArray:
    # `general_pool * 0.0` (rather than a bare `0.0`) preserves the
    # scalar/array shape of `general_pool` for the vectorized forward loop.
    if not withdrawal_started or cumulative_1_plus_g_over_1_plus_r == 0.0:
        return general_pool * 0.0
    return general_pool / cumulative_1_plus_g_over_1_plus_r
