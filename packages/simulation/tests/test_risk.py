import math
from decimal import Decimal

import numpy as np
from core.models import (
    RISK_TOLERANCE_END_RRA,
    RISK_TOLERANCE_START_RRA,
    RiskConfig,
)
from simulation.risk import (
    legacy_rra,
    risk_tolerance_to_rra,
    rra_by_month,
)


def test_endpoints_are_pinned_rra_values():
    # By construction rt=1 -> start_rra, rt=24 -> end_rra.
    conservative_tolerance = 1.0
    aggressive_tolerance = 24.0

    assert risk_tolerance_to_rra(conservative_tolerance) == RISK_TOLERANCE_START_RRA
    assert risk_tolerance_to_rra(aggressive_tolerance) == RISK_TOLERANCE_END_RRA


def test_zero_tolerance_is_infinite_rra():
    assert math.isinf(risk_tolerance_to_rra(0.0))


def test_rra_is_monotonic_decreasing_in_tolerance():
    values = [risk_tolerance_to_rra(rt) for rt in range(1, 25)]
    assert all(
        earlier > later for earlier, later in zip(values, values[1:], strict=False)
    )


def test_rra_by_month_flat_when_no_age_delta():
    config = RiskConfig()  # delta_at_max_age == 0
    num_months = 12

    result = rra_by_month(
        config, num_months=num_months, current_age_months=360, max_age_months=1200
    )

    expected = risk_tolerance_to_rra(float(config.risk_tolerance_at_20))
    assert result.shape == (num_months,)
    assert np.allclose(result, expected)


def test_legacy_rra_uses_legacy_delta():
    risk_tolerance_at_20 = Decimal(12)
    legacy_delta_from_at_20 = Decimal(-4)
    config = RiskConfig(
        risk_tolerance_at_20=risk_tolerance_at_20,
        legacy_delta_from_at_20=legacy_delta_from_at_20,
    )

    assert legacy_rra(config) == risk_tolerance_to_rra(
        float(risk_tolerance_at_20 + legacy_delta_from_at_20)
    )


def test_legacy_rra_floors_at_zero_tolerance_for_extreme_negative_delta():
    # A legacy delta that would push tolerance below 0 must floor at 0
    # (infinite RRA / 0% stocks), matching _interpolate_risk_tolerance's
    # clamp, rather than extrapolating the log-scale formula past its
    # calibrated range.
    risk_tolerance_at_20 = Decimal(12)
    legacy_delta_from_at_20 = Decimal(-20)
    config = RiskConfig(
        risk_tolerance_at_20=risk_tolerance_at_20,
        legacy_delta_from_at_20=legacy_delta_from_at_20,
    )

    assert legacy_rra(config) == risk_tolerance_to_rra(0.0)
