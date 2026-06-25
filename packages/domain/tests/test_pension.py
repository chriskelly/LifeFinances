from __future__ import annotations

from decimal import Decimal

from core.job import AgeFactor
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)


def test_calstrs_table_spans_55_to_65_and_is_monotonic() -> None:
    youngest_age_months = 55 * 12
    oldest_age_months = 65 * 12

    ages = [age for age, _ in CALSTRS_2_AT_62_AGE_FACTORS]
    factors = [factor for _, factor in CALSTRS_2_AT_62_AGE_FACTORS]

    assert ages[0] == youngest_age_months
    assert ages[-1] == oldest_age_months
    assert factors == sorted(factors)


def test_age_factors_from_statutory_builds_config_models() -> None:
    rows = ((62 * 12, Decimal("0.0200")), (65 * 12, Decimal("0.0240")))

    result = age_factors_from_statutory(rows)

    assert result == [
        AgeFactor(age_months=62 * 12, factor=Decimal("0.0200")),
        AgeFactor(age_months=65 * 12, factor=Decimal("0.0240")),
    ]
