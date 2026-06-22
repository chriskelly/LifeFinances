from __future__ import annotations

from decimal import Decimal

import pytest
from core.job import Job
from pydantic import ValidationError


def test_job_rejects_tax_deferred_above_income() -> None:
    income = Decimal("100000")
    too_much_deferred = income + Decimal("1")

    with pytest.raises(ValidationError):
        Job(annual_income=income, annual_tax_deferred=too_much_deferred)


def test_job_allows_tax_deferred_equal_to_income() -> None:
    income = Decimal("100000")

    job = Job(annual_income=income, annual_tax_deferred=income)

    assert job.annual_tax_deferred == income
