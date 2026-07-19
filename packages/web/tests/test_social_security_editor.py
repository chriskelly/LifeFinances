from decimal import Decimal

from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from core.social_security import AnnualEarnings
from fastapi.testclient import TestClient
from web.forms import CLAIM_AGE_MONTHS, CLAIM_AGE_YEARS, SS_EARNINGS_FILE
from web.routes import (
    EDITOR_SOCIAL_SECURITY,
    PLAN_SOCIAL_SECURITY,
    PLAN_SS_EARNINGS,
)
from web.sections import SOCIAL_SECURITY_TITLE


def _statement_xml(years: list[int]) -> str:
    rows = "\n".join(
        f'    <osss:Earnings startYear="{year}" endYear="{year}">'
        f"<osss:FicaEarnings>50000</osss:FicaEarnings></osss:Earnings>"
        for year in years
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<osss:OnlineSocialSecurityStatementData "
        'xmlns:osss="http://ssa.gov/osss/schemas/2.0">\n'
        "  <osss:EarningsRecord>\n"
        f"{rows}\n"
        "  </osss:EarningsRecord>\n"
        "</osss:OnlineSocialSecurityStatementData>\n"
    )


def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id


def test_patch_claim_age_persists_total_months_and_keeps_earnings(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    kept_year = 2019
    seeded.household.person1.social_security.earnings_record = [
        AnnualEarnings(year=kept_year, fica_earnings=Decimal("40000"))
    ]
    repo.save(plan_id, seeded)
    claim_years = 65
    claim_months = 6

    response = client.patch(
        f"{PLAN_SOCIAL_SECURITY}?plan={plan_id}&person=person1",
        data={CLAIM_AGE_YEARS: str(claim_years), CLAIM_AGE_MONTHS: str(claim_months)},
    )

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    config = after.household.person1.social_security
    assert config.claim_age_months == claim_years * 12 + claim_months
    assert config.earnings_record[0].year == kept_year


def test_upload_statement_replaces_earnings_and_triggers_refresh(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_years = [2020, 2023]

    response = client.post(
        f"{PLAN_SS_EARNINGS}?plan={plan_id}&person=person1",
        files={
            SS_EARNINGS_FILE: (
                "statement.xml",
                _statement_xml(expected_years),
                "text/xml",
            )
        },
    )

    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "planUpdated"
    after = repo.get_by_id(plan_id)
    assert after is not None
    years = [e.year for e in after.household.person1.social_security.earnings_record]
    assert years == expected_years


def test_upload_invalid_xml_returns_422_without_changing_earnings(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    kept_year = 2019
    seeded_fica = Decimal("40000")
    seeded_record = [AnnualEarnings(year=kept_year, fica_earnings=seeded_fica)]
    seeded.household.person1.social_security.earnings_record = seeded_record
    repo.save(plan_id, seeded)

    response = client.post(
        f"{PLAN_SS_EARNINGS}?plan={plan_id}&person=person1",
        files={SS_EARNINGS_FILE: ("bad.xml", "<not-valid", "text/xml")},
    )

    assert response.status_code == 422
    assert 'class="form-error"' in response.text
    assert 'role="alert"' in response.text
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household.person1.social_security.earnings_record == seeded_record


def test_editor_social_security_get_renders_section(
    client: TestClient, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{EDITOR_SOCIAL_SECURITY}?plan={plan_id}")

    assert response.status_code == 200
    assert SOCIAL_SECURITY_TITLE in response.text
