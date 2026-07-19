from decimal import Decimal

from core.job import Job
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)
from fastapi.testclient import TestClient
from web.routes import EDITOR_JOBS, PLAN_JOBS
from web.sections import JOBS_TITLE


def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id


def test_patch_jobs_adds_job_to_person1(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
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


def test_patch_jobs_empty_form_clears_jobs(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.household.person1.jobs = [Job(annual_income=Decimal("100000"))]
    repo.save(plan_id, seeded)

    response = client.patch(f"{PLAN_JOBS}?plan={plan_id}&person=person1", data={})

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household.person1.jobs == []


def test_patch_jobs_attaches_calstrs_pension(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_table = age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS)
    data = {
        "jobs[0].annual_income": "100000",
        "jobs[0].start_kind": "now",
        "jobs[0].end_kind": "none",
        "jobs[0].pension_enabled": "on",
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


def test_patch_jobs_for_absent_partner_returns_422(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
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


def test_editor_jobs_get_renders_section(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{EDITOR_JOBS}?plan={plan_id}")

    assert response.status_code == 200
    assert JOBS_TITLE in response.text
