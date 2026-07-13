from __future__ import annotations

import numpy as np

_SOURCE_KEYS = ("job", "social_security", "pension", "manual")


def prorate_net_income_by_source(
    *,
    gross_job: np.ndarray,
    gross_social_security: np.ndarray,
    gross_pension: np.ndarray,
    gross_manual: np.ndarray,
    taxes: np.ndarray,
) -> dict[str, np.ndarray]:
    """Split net income by source. `taxes` are domain-signed (non-positive)."""
    gross = {
        "job": gross_job,
        "social_security": gross_social_security,
        "pension": gross_pension,
        "manual": gross_manual,
    }
    total_gross = gross_job + gross_social_security + gross_pension + gross_manual
    nets: dict[str, np.ndarray] = {}
    for key in _SOURCE_KEYS:
        net = np.zeros_like(total_gross, dtype=np.float64)
        positive = total_gross > 0.0
        share = np.zeros_like(total_gross, dtype=np.float64)
        share[positive] = gross[key][positive] / total_gross[positive]
        net[positive] = gross[key][positive] + taxes[positive] * share[positive]
        nets[key] = net
    return nets
