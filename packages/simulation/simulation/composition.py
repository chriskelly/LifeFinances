from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from simulation.npv import backward_npv_including_current

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


@dataclass(frozen=True)
class WealthBySource:
    job: np.ndarray
    social_security: np.ndarray
    pension: np.ndarray
    manual: np.ndarray


def wealth_by_income_source(
    *,
    gross_job: np.ndarray,
    gross_social_security: np.ndarray,
    gross_pension: np.ndarray,
    gross_manual: np.ndarray,
    taxes: np.ndarray,
    monthly_inflation: float,
    monthly_bond_rate: float,
) -> WealthBySource:
    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_social_security,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        taxes=taxes,
    )
    months = gross_job.shape[0]
    deflator = (1.0 + monthly_inflation) ** np.arange(months, dtype=np.float64)
    one_over = 1.0 / (1.0 + monthly_bond_rate)
    bands = {
        key: backward_npv_including_current(
            nets[key] / deflator, one_over_1_plus_r=one_over
        )
        for key in _SOURCE_KEYS
    }
    return WealthBySource(
        job=bands["job"],
        social_security=bands["social_security"],
        pension=bands["pension"],
        manual=bands["manual"],
    )
