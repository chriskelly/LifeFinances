from __future__ import annotations

import math

import numpy as np
from core.models import (
    RISK_TOLERANCE_END_RRA,
    RISK_TOLERANCE_NUM_VALUES,
    RISK_TOLERANCE_START_RRA,
    RiskConfig,
)


def _ln_one_over(x: float) -> float:
    return math.log(1.0 / x)


def risk_tolerance_to_rra(risk_tolerance: float) -> float:
    """Map the user-facing risk tolerance slider (1-24) to relative risk aversion (RRA).

    Tolerance 0 maps to infinity (0% stocks). For 1-24, RRA is computed on a
    log scale pinned at two endpoints: tolerance 1 -> start RRA (16.0),
    tolerance 24 -> end RRA (0.5). ``shift`` anchors the curve at the conservative
    end; ``scale`` stretches the axis so the aggressive end lands on target.
    """
    if risk_tolerance == 0.0:
        return math.inf
    shift = _ln_one_over(RISK_TOLERANCE_START_RRA)
    scale = (RISK_TOLERANCE_NUM_VALUES - 2.0) / (
        _ln_one_over(RISK_TOLERANCE_END_RRA) - _ln_one_over(RISK_TOLERANCE_START_RRA)
    )
    return 1.0 / math.exp((risk_tolerance - 1.0) / scale + shift)


def _interpolate_risk_tolerance(
    config: RiskConfig,
    *,
    age_months: float,
    max_age_months: int,
) -> float:
    at_20 = float(config.risk_tolerance_at_20)
    if max_age_months <= 20 * 12:
        return max(0.0, at_20)
    at_max = at_20 + float(config.delta_at_max_age)
    fraction = (age_months - 20.0 * 12.0) / (max_age_months - 20.0 * 12.0)
    # Clamp so the glide plateaus at `at_max` once the horizon-defining
    # person reaches max age, rather than extrapolating past it.
    fraction = min(1.0, max(0.0, fraction))
    return max(0.0, at_20 + (at_max - at_20) * fraction)


def rra_by_month(
    config: RiskConfig,
    *,
    num_months: int,
    current_age_months: int,
    max_age_months: int,
) -> np.ndarray:
    result = np.empty(num_months, dtype=np.float64)
    for month in range(num_months):
        risk_tolerance = _interpolate_risk_tolerance(
            config,
            age_months=current_age_months + month,
            max_age_months=max_age_months,
        )
        result[month] = risk_tolerance_to_rra(risk_tolerance)
    return result


def legacy_rra(config: RiskConfig) -> float:
    risk_tolerance = float(config.risk_tolerance_at_20) + float(
        config.legacy_delta_from_at_20
    )
    # Floor at 0 (infinite RRA / 0% stocks), matching the age-glide path's
    # clamp — a sufficiently negative legacy delta must not extrapolate the
    # log-scale formula past its calibrated [0, 24] range.
    return risk_tolerance_to_rra(max(0.0, risk_tolerance))
