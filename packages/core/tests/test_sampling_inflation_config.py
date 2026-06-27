from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.models import (
    InflationConfig,
    Plan,
    SamplingConfig,
)
from pydantic import ValidationError


def test_sampling_rejects_non_positive_block_size() -> None:
    with pytest.raises(ValidationError):
        SamplingConfig(block_size_months=0)


def test_sampling_rejects_non_positive_num_runs() -> None:
    with pytest.raises(ValidationError):
        SamplingConfig(num_runs=0)


def test_inflation_defaults_to_suggested() -> None:
    config = InflationConfig()

    assert config.mode == "suggested"
    assert config.manual_annual_rate is None


def test_inflation_manual_requires_rate() -> None:
    with pytest.raises(ValidationError):
        InflationConfig(mode="manual")


def test_inflation_manual_accepts_rate() -> None:
    expected_rate = Decimal("0.025")

    config = InflationConfig(mode="manual", manual_annual_rate=expected_rate)

    assert config.manual_annual_rate == expected_rate


def test_plan_gets_default_sampling_and_inflation() -> None:
    plan = default_plan()

    assert plan.sampling == SamplingConfig()
    assert plan.inflation == InflationConfig()


def test_older_plan_json_without_configs_fills_defaults() -> None:
    plan = default_plan()
    payload = plan.model_dump()
    del payload["sampling"]
    del payload["inflation"]

    rehydrated = Plan.model_validate(payload)

    assert rehydrated.sampling == SamplingConfig()
    assert rehydrated.inflation == InflationConfig()
