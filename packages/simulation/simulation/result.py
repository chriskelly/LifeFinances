from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

import numpy as np
from core.models import PlanningPreset
from pydantic import BaseModel, ConfigDict

from simulation.market_data.cache import MarketDataSource
from simulation.market_data.inflation import InflationResolved
from simulation.planning_returns import PlanningReturns

ENGINE_VERSION = "phase3d"

RAW_ARRAY_FIELDS = (
    "balance_start",
    "withdrawals_essential",
    "withdrawals_discretionary",
    "withdrawals_general",
    "withdrawals_total",
    "savings_stock_allocation",
)

_PUBLIC_ARRAY_FIELDS = (
    *RAW_ARRAY_FIELDS,
    "wealth_job",
    "wealth_social_security",
    "wealth_pension",
    "wealth_manual",
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


class RawSimulationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ran_at: datetime
    horizon_months: int
    num_runs: int
    balance_start: np.ndarray
    withdrawals_essential: np.ndarray
    withdrawals_discretionary: np.ndarray
    withdrawals_general: np.ndarray
    withdrawals_total: np.ndarray
    savings_stock_allocation: np.ndarray
    num_runs_insufficient: int
    engine_version: str = ENGINE_VERSION

    def __eq__(self, other: Any) -> bool:
        # Pydantic's generated __eq__ compares fields with `==`, which raises
        # on np.ndarray fields ("truth value of an array is ambiguous").
        if not isinstance(other, RawSimulationResult):
            return NotImplemented
        return _eq_ndarray_model(self, other, array_fields=RAW_ARRAY_FIELDS)


class ResolvedAssumptions(BaseModel):
    annual_inflation: float
    annual_stock_return: float
    annual_bond_return: float
    annual_stock_log_variance: float
    planning_preset: PlanningPreset
    inflation_source: Literal["manual", "live", "cache", "vendored"]
    inflation_observation_date: date | None = None
    sp500_source: MarketDataSource | None = None
    sp500_observation_date: date | None = None
    treasury_source: MarketDataSource | None = None
    treasury_observation_date: date | None = None


def build_resolved_assumptions(
    *,
    inflation: InflationResolved,
    planning: PlanningReturns,
    preset: PlanningPreset,
) -> ResolvedAssumptions:
    inflation_source = (
        "manual" if inflation.source == "manual" else inflation.market_source
    )
    if inflation_source is None:
        raise ValueError("suggested inflation is missing market provenance")
    return ResolvedAssumptions(
        annual_inflation=inflation.annual,
        annual_stock_return=planning.annual_stocks,
        annual_bond_return=planning.annual_bonds,
        annual_stock_log_variance=planning.annual_stock_log_variance,
        planning_preset=preset,
        inflation_source=inflation_source,
        inflation_observation_date=inflation.observation_date,
        sp500_source=planning.sp500.source if planning.sp500 else None,
        sp500_observation_date=(
            planning.sp500.observation_date if planning.sp500 else None
        ),
        treasury_source=planning.treasury.source if planning.treasury else None,
        treasury_observation_date=(
            planning.treasury.observation_date if planning.treasury else None
        ),
    )


class SimulationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ran_at: datetime
    horizon_months: int
    num_runs: int
    percentiles: list[int]
    start_month: tuple[int, int]
    balance_start: np.ndarray
    withdrawals_essential: np.ndarray
    withdrawals_discretionary: np.ndarray
    withdrawals_general: np.ndarray
    withdrawals_total: np.ndarray
    savings_stock_allocation: np.ndarray
    wealth_job: np.ndarray
    wealth_social_security: np.ndarray
    wealth_pension: np.ndarray
    wealth_manual: np.ndarray
    num_runs_insufficient: int
    resolved_assumptions: ResolvedAssumptions
    engine_version: str = ENGINE_VERSION

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SimulationResult):
            return NotImplemented
        return _eq_ndarray_model(self, other, array_fields=_PUBLIC_ARRAY_FIELDS)
