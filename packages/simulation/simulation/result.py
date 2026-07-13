from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

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
    expected_type: type[Any],
    array_fields: tuple[str, ...],
) -> bool:
    if not isinstance(other, expected_type):
        return NotImplemented
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
        return _eq_ndarray_model(
            self,
            other,
            expected_type=RawSimulationResult,
            array_fields=RAW_ARRAY_FIELDS,
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
    engine_version: str = ENGINE_VERSION

    def __eq__(self, other: Any) -> bool:
        return _eq_ndarray_model(
            self,
            other,
            expected_type=SimulationResult,
            array_fields=_PUBLIC_ARRAY_FIELDS,
        )
