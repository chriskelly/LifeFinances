from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

STUB_VERSION = "phase1"


class SimulationResult(BaseModel):
    ran_at: datetime
    horizon_months: int
    echo: dict[str, Any]
    stub_version: str = STUB_VERSION
