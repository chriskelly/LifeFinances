from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

from simulation.preprocess import ProcessedPlan

RRA_INFINITE_SENTINEL = 1e300

DIAGNOSTICS_ARRAY_FIELDS: tuple[str, ...] = (
    "rra_by_month",
    "stock_allocation_total_portfolio",
    "scheduled_wealth",
    "elasticity_discretionary",
    "elasticity_legacy",
    "savings_balance",
    "income_npv",
    "wealth_base",
    "essential_reserve",
    "discretionary_reserve",
    "legacy_reserve",
    "discretionary_pool",
    "legacy_pool",
    "general_pool",
    "stocks_target",
    "expected_savings_stock_fraction",
)


def _eq_ndarray_model(
    self: Any,
    other: Any,
    *,
    array_fields: tuple[str, ...],
) -> bool:
    """Compare two same-typed models whose ndarray fields break Pydantic's `==`.

    Callers guard the type check (returning `NotImplemented` on mismatch) so this
    helper always compares two instances of the same model and returns a real bool.
    """
    if not all(
        np.array_equal(getattr(self, field), getattr(other, field))
        for field in array_fields
    ):
        return False
    scalar_fields = set(type(self).model_fields) - set(array_fields)
    return all(getattr(self, field) == getattr(other, field) for field in scalar_fields)


class SimulationDiagnostics(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    rra_by_month: np.ndarray
    stock_allocation_total_portfolio: np.ndarray
    legacy_stock_allocation: float
    scheduled_wealth: np.ndarray
    elasticity_discretionary: np.ndarray
    elasticity_legacy: np.ndarray
    savings_balance: np.ndarray
    income_npv: np.ndarray
    wealth_base: np.ndarray
    essential_reserve: np.ndarray
    discretionary_reserve: np.ndarray
    legacy_reserve: np.ndarray
    discretionary_pool: np.ndarray
    legacy_pool: np.ndarray
    general_pool: np.ndarray
    stocks_target: np.ndarray
    expected_savings_stock_fraction: np.ndarray

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SimulationDiagnostics):
            return NotImplemented
        return _eq_ndarray_model(self, other, array_fields=DIAGNOSTICS_ARRAY_FIELDS)


def rra_for_diagnostics(rra: np.ndarray) -> np.ndarray:
    return np.where(np.isinf(rra), RRA_INFINITE_SENTINEL, rra).astype(np.float64)


def empty_diagnostics(*, months: int) -> SimulationDiagnostics:
    zeros = np.zeros(months, dtype=np.float64)
    return SimulationDiagnostics(
        rra_by_month=zeros.copy(),
        stock_allocation_total_portfolio=zeros.copy(),
        legacy_stock_allocation=0.0,
        scheduled_wealth=zeros.copy(),
        elasticity_discretionary=zeros.copy(),
        elasticity_legacy=zeros.copy(),
        savings_balance=zeros.copy(),
        income_npv=zeros.copy(),
        wealth_base=zeros.copy(),
        essential_reserve=zeros.copy(),
        discretionary_reserve=zeros.copy(),
        legacy_reserve=zeros.copy(),
        discretionary_pool=zeros.copy(),
        legacy_pool=zeros.copy(),
        general_pool=zeros.copy(),
        stocks_target=zeros.copy(),
        expected_savings_stock_fraction=zeros.copy(),
    )


def build_diagnostics(
    *,
    processed: ProcessedPlan,
    scheduled_wealth: np.ndarray,
    elasticity_discretionary: np.ndarray,
    elasticity_legacy: np.ndarray,
    savings_balance: np.ndarray,
    income_npv: np.ndarray,
    wealth_base: np.ndarray,
    essential_reserve: np.ndarray,
    discretionary_reserve: np.ndarray,
    legacy_reserve: np.ndarray,
    discretionary_pool: np.ndarray,
    legacy_pool: np.ndarray,
    general_pool: np.ndarray,
    stocks_target: np.ndarray,
    expected_savings_stock_fraction: np.ndarray,
) -> SimulationDiagnostics:
    return SimulationDiagnostics(
        rra_by_month=rra_for_diagnostics(processed.rra),
        stock_allocation_total_portfolio=np.asarray(
            processed.stock_allocation_total_portfolio, dtype=np.float64
        ).copy(),
        legacy_stock_allocation=float(processed.legacy_stock_allocation),
        scheduled_wealth=np.asarray(scheduled_wealth, dtype=np.float64).copy(),
        elasticity_discretionary=np.asarray(
            elasticity_discretionary, dtype=np.float64
        ).copy(),
        elasticity_legacy=np.asarray(elasticity_legacy, dtype=np.float64).copy(),
        savings_balance=np.asarray(savings_balance, dtype=np.float64).copy(),
        income_npv=np.asarray(income_npv, dtype=np.float64).copy(),
        wealth_base=np.asarray(wealth_base, dtype=np.float64).copy(),
        essential_reserve=np.asarray(essential_reserve, dtype=np.float64).copy(),
        discretionary_reserve=np.asarray(
            discretionary_reserve, dtype=np.float64
        ).copy(),
        legacy_reserve=np.asarray(legacy_reserve, dtype=np.float64).copy(),
        discretionary_pool=np.asarray(discretionary_pool, dtype=np.float64).copy(),
        legacy_pool=np.asarray(legacy_pool, dtype=np.float64).copy(),
        general_pool=np.asarray(general_pool, dtype=np.float64).copy(),
        stocks_target=np.asarray(stocks_target, dtype=np.float64).copy(),
        expected_savings_stock_fraction=np.asarray(
            expected_savings_stock_fraction, dtype=np.float64
        ).copy(),
    )
