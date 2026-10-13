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


def manual_stream_basis_adjustment(
    *,
    manual_gross_real: np.ndarray,
    gross_manual: np.ndarray,
) -> np.ndarray:
    """Delta that converts the domain's own-basis manual total to real
    (today's-dollars): `manual_gross_real - gross_manual`.

    Job, Social Security, and pension income are already today's-dollars real,
    so they are used as-is; manual income streams carry their own `is_nominal`
    basis and are the only ones that need converting. Shared by `preprocess.py`
    (net cashflow) and `real_net_income_by_source` below (net-income flows; also
    the manual wealth band, via `wealth_by_income_source`) so every consumer
    applies the identical correction.
    """
    return manual_gross_real - gross_manual


def real_net_income_by_source(
    *,
    gross_job: np.ndarray,
    gross_social_security: np.ndarray,
    gross_pension: np.ndarray,
    gross_manual: np.ndarray,
    taxes: np.ndarray,
    manual_gross_real: np.ndarray,
) -> dict[str, np.ndarray]:
    """Real monthly net income split by source.

    The domain produces today's-dollars (real) amounts for job, Social Security,
    and pension, so they are not deflated. Taxes are computed on that real income
    with a constant real bracket set and pass through too — except that a manual
    stream declared nominal is taxed on its nominal face amount, which this
    split does not re-base. The four returned flows sum to the real net cashflow
    (gross income plus domain-signed taxes), with each month's tax prorated by
    gross share — exactly where that month's total gross income is positive; in
    a zero-gross month `prorate_net_income_by_source` yields zero flows and any
    residual tax is not attributed. The manual flow honors each stream's own
    real/nominal basis via `manual_stream_basis_adjustment`. Shared by
    `wealth_by_income_source` and `build_diagnostics`.
    """
    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_social_security,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        taxes=taxes,
    )
    nets["manual"] = nets["manual"] + manual_stream_basis_adjustment(
        manual_gross_real=manual_gross_real,
        gross_manual=gross_manual,
    )
    return nets


def wealth_by_income_source(
    *,
    gross_job: np.ndarray,
    gross_social_security: np.ndarray,
    gross_pension: np.ndarray,
    gross_manual: np.ndarray,
    taxes: np.ndarray,
    monthly_bond_rate: float,
    manual_gross_real: np.ndarray,
) -> WealthBySource:
    real_nets = real_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_social_security,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        taxes=taxes,
        manual_gross_real=manual_gross_real,
    )
    one_over = 1.0 / (1.0 + monthly_bond_rate)
    bands = {
        key: backward_npv_including_current(real_nets[key], one_over_1_plus_r=one_over)
        for key in _SOURCE_KEYS
    }
    return WealthBySource(
        job=bands["job"],
        social_security=bands["social_security"],
        pension=bands["pension"],
        manual=bands["manual"],
    )
