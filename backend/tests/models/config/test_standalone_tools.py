"""Tests for app.models.config.standalone_tools."""

import pytest
from pydantic import ValidationError

from app.models.config.standalone_tools import DisabilityCoverage


def test_disability_coverage_default() -> None:
    cov = DisabilityCoverage()
    assert cov.percentage == 0.0
    assert cov.duration_years is None
    assert cov.age_limit is None


def test_disability_coverage_duration_only() -> None:
    cov = DisabilityCoverage(percentage=60.0, duration_years=5)
    assert cov.duration_years == 5
    assert cov.age_limit is None


def test_disability_coverage_age_only() -> None:
    cov = DisabilityCoverage(percentage=50.0, age_limit=65)
    assert cov.age_limit == 65
    assert cov.duration_years is None


def test_disability_coverage_both_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        DisabilityCoverage(percentage=60.0, duration_years=5, age_limit=65)


def test_disability_coverage_positive_percentage_neither_mode() -> None:
    with pytest.raises(ValidationError):
        DisabilityCoverage(percentage=60.0)


def test_disability_coverage_zero_percentage_with_duration_rejected() -> None:
    with pytest.raises(ValidationError):
        DisabilityCoverage(percentage=0.0, duration_years=5)


def test_disability_coverage_non_positive_duration_rejected() -> None:
    with pytest.raises(ValidationError):
        DisabilityCoverage(percentage=60.0, duration_years=0)
