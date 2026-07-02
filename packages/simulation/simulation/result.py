from __future__ import annotations

from datetime import datetime

import numpy as np
from pydantic import BaseModel, ConfigDict

ENGINE_VERSION = "phase3b"


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
