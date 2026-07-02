from decimal import Decimal

from core.defaults import default_plan
from core.models import (
    DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT,
    DEFAULT_DELTA_AT_MAX_AGE,
    DEFAULT_LEGACY_DELTA_FROM_AT_20,
    DEFAULT_RISK_TOLERANCE_AT_20,
    DEFAULT_TIME_PREFERENCE,
    RISK_TOLERANCE_END_RRA,
    RISK_TOLERANCE_NUM_VALUES,
    RISK_TOLERANCE_START_RRA,
    PlanningReturnsConfig,
    RiskConfig,
)


def test_risk_config_defaults_match_constants():
    config = RiskConfig()

    assert config.risk_tolerance_at_20 == DEFAULT_RISK_TOLERANCE_AT_20
    assert config.delta_at_max_age == DEFAULT_DELTA_AT_MAX_AGE
    assert config.legacy_delta_from_at_20 == DEFAULT_LEGACY_DELTA_FROM_AT_20
    assert config.time_preference == DEFAULT_TIME_PREFERENCE
    assert config.additional_annual_spending_tilt == (
        DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT
    )


def test_pinned_rra_constants():
    # pinned: tpaw get_test_plan_params_server constants
    assert RISK_TOLERANCE_NUM_VALUES == 25
    assert RISK_TOLERANCE_START_RRA == 16.0
    assert RISK_TOLERANCE_END_RRA == 0.5


def test_plan_has_tpaw_blocks_with_defaults():
    plan = default_plan()
    expected_legacy_target = Decimal(0)

    assert isinstance(plan.risk, RiskConfig)
    assert isinstance(plan.planning_returns, PlanningReturnsConfig)
    assert plan.extra_essential_spending == []
    assert plan.extra_discretionary_spending == []
    assert plan.legacy_target == expected_legacy_target
