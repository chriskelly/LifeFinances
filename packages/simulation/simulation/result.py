from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

ENGINE_VERSION = "phase3b"

_ARRAY_FIELDS = (
    "balance_start",
    "withdrawals_essential",
    "withdrawals_discretionary",
    "withdrawals_general",
    "withdrawals_total",
    "savings_stock_allocation",
)


class SimulationResult(BaseModel):
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
        # Compare array fields with np.array_equal and everything else normally.
        if not isinstance(other, SimulationResult):
            return NotImplemented
        if not all(
            np.array_equal(getattr(self, field), getattr(other, field))
            for field in _ARRAY_FIELDS
        ):
            return False
        scalar_fields = set(type(self).model_fields) - set(_ARRAY_FIELDS)
        return all(
            getattr(self, field) == getattr(other, field) for field in scalar_fields
        )
