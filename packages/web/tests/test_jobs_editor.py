from decimal import Decimal

from core.job import Job
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)
from fastapi.testclient import TestClient
from web.currency import format_usd
from web.percent import format_percent
from web.routes import EDITOR_JOBS, PLAN_JOBS
from web.sections import JOBS_TITLE

from web import forms


def test_patch_jobs_adds_job_to_person1(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    expected_label = "Engineer"
    expected_income = "150000"
    data = {
        "jobs[0].label": expected_label,
        "jobs[0].annual_income": expected_income,
        "jobs[0].annual_tax_deferred": "0",
        "jobs[0].annual_raise": "0",
        "jobs[0].social_security_eligible": "on",
        "jobs[0].start_kind": "now",
        "jobs[0].end_kind": "none",
    }

    response = client.patch(f"{PLAN_JOBS}?plan={plan_id}&person=person1", data=data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    jobs = after.household.person1.jobs
    assert [j.label for j in jobs] == [expected_label]
    assert jobs[0].annual_income == Decimal(expected_income)


def test_patch_jobs_blank_annual_income_returns_422(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    expected_income = Decimal("150000")
    job_start = CalendarMonthBoundary(year=2010, month=1)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.household.person1.jobs = [
        Job(annual_income=expected_income, start=job_start)
    ]
    repo.save(plan_id, seeded)
    invalid_income = ""

    response = client.patch(
        f"{PLAN_JOBS}?plan={plan_id}&person=person1",
        data={
            "jobs[0].annual_income": invalid_income,
            "jobs[0].start_kind": "now",
            "jobs[0].end_kind": "none",
        },
    )

    assert response.status_code == 422
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household.person1.jobs[0].annual_income == expected_income


def test_patch_jobs_empty_form_clears_jobs(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    job_start = CalendarMonthBoundary(year=2010, month=1)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.household.person1.jobs = [
        Job(annual_income=Decimal("100000"), start=job_start)
    ]
    repo.save(plan_id, seeded)

    response = client.patch(f"{PLAN_JOBS}?plan={plan_id}&person=person1", data={})

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household.person1.jobs == []


def test_patch_jobs_attaches_calstrs_pension(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    expected_table = age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS)
    pension_preset = forms.PENSION_CALSTRS_2_AT_62
    data = {
        "jobs[0].annual_income": "100000",
        "jobs[0].start_kind": "now",
        "jobs[0].end_kind": "none",
        "jobs[0].pension": pension_preset,
        "jobs[0].pension_service_start_kind": "calendar_month",
        "jobs[0].pension_service_start_year": "2015",
        "jobs[0].pension_service_start_month": "8",
        "jobs[0].pension_claim_kind": "person_age",
        "jobs[0].pension_claim_person": "person1",
        "jobs[0].pension_claim_age_years": "62",
        "jobs[0].pension_claim_age_months": "0",
    }

    response = client.patch(f"{PLAN_JOBS}?plan={plan_id}&person=person1", data=data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    pension = after.household.person1.jobs[0].pension
    assert pension is not None
    assert pension.age_factor_table == expected_table


def test_editor_jobs_pension_dropdown_defaults_to_none(
    client: TestClient, plan_id: int
) -> None:

    response = client.get(f"{EDITOR_JOBS}?plan={plan_id}")

    assert response.status_code == 200
    assert forms.PENSION_LABEL in response.text
    assert f'value="{forms.PENSION_NONE}"' in response.text
    assert f">{forms.PENSION_NONE_LABEL}</option>" in response.text
    assert f'value="{forms.PENSION_CALSTRS_2_AT_62}"' in response.text
    assert f">{forms.PENSION_CALSTRS_2_AT_62_LABEL}</option>" in response.text


def test_patch_jobs_for_absent_partner_returns_422(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    single = repo.get_by_id(plan_id)
    assert single is not None
    single.household.person2 = None
    repo.save(plan_id, single)

    response = client.patch(
        f"{PLAN_JOBS}?plan={plan_id}&person=person2",
        data={
            "jobs[0].annual_income": "1000",
            "jobs[0].start_kind": "now",
            "jobs[0].end_kind": "none",
        },
    )

    assert response.status_code == 422


def test_editor_jobs_formats_income_as_usd(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    income = Decimal("150000")
    expected_display = format_usd(income)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.household.person1.jobs = [
        Job(annual_income=income, start=CalendarMonthBoundary(year=2010, month=1))
    ]
    repo.save(plan_id, seeded)

    response = client.get(f"{EDITOR_JOBS}?plan={plan_id}")

    assert response.status_code == 200
    assert f'value="{expected_display}"' in response.text
    assert "checkbox-label" in response.text


def test_editor_jobs_formats_raise_as_percent(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    raise_rate = Decimal("0.035")
    expected_display = format_percent(raise_rate)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.household.person1.jobs = [
        Job(
            annual_income=Decimal("100000"),
            annual_raise=raise_rate,
            start=CalendarMonthBoundary(year=2010, month=1),
        )
    ]
    repo.save(plan_id, seeded)

    response = client.get(f"{EDITOR_JOBS}?plan={plan_id}")

    assert response.status_code == 200
    assert f'value="{expected_display}"' in response.text


def test_editor_jobs_get_renders_section(client: TestClient, plan_id: int) -> None:

    response = client.get(f"{EDITOR_JOBS}?plan={plan_id}")

    assert response.status_code == 200
    assert JOBS_TITLE in response.text


def test_editor_jobs_start_omits_plan_start_option(
    client: TestClient, plan_id: int
) -> None:

    response = client.get(f"{EDITOR_JOBS}?plan={plan_id}")

    assert response.status_code == 200
    assert "Plan start" not in response.text
    assert "Plan horizon" in response.text
    assert 'value="now"' in response.text
