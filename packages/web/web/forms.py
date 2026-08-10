from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import get_args

from core.job import Job
from core.models import (
    AppSettings,
    FilingStatus,
    Household,
    PersonHousehold,
    Plan,
    Portfolio,
)
from core.streams import PersonId, TimedStream
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)
from domain.statutory.taxes import STATE_BRACKETS
from pydantic import BaseModel
from starlette.datastructures import FormData

from web import boundaries
from web.currency import parse_usd
from web.percent import parse_percent

JOBS_PREFIX = "jobs"
STREAMS_PREFIX = "streams"
_TRUE = {"on", "true", "1"}

# Field-name constants for templates/tests — must match DTO field names
PERSON1_BIRTH_MONTH = "person1_birth_month"
PERSON1_BIRTH_YEAR = "person1_birth_year"
PERSON1_MAX_AGE_YEARS = "person1_max_age_years"
PERSON2_BIRTH_MONTH = "person2_birth_month"
PERSON2_BIRTH_YEAR = "person2_birth_year"
PERSON2_MAX_AGE_YEARS = "person2_max_age_years"
HAS_PARTNER = "has_partner"
FILING_STATUS = "filing_status"
RESIDENCE_STATE = "residence_state"
SS_PENSION_TAXABLE_FRACTION = "ss_pension_taxable_fraction"
SOCIAL_SECURITY_TRUST_FACTOR = "social_security_trust_factor"

FILING_STATUSES: tuple[FilingStatus, ...] = get_args(FilingStatus)
FILING_STATUS_LABELS = {
    "single": "Single",
    "married_filing_jointly": "Married filing jointly",
}
MONTH_ABBREVIATIONS: tuple[tuple[int, str], ...] = (
    (1, "Jan"),
    (2, "Feb"),
    (3, "Mar"),
    (4, "Apr"),
    (5, "May"),
    (6, "Jun"),
    (7, "Jul"),
    (8, "Aug"),
    (9, "Sep"),
    (10, "Oct"),
    (11, "Nov"),
    (12, "Dec"),
)
TAX_MODELED_STATES: tuple[str, ...] = tuple(sorted(STATE_BRACKETS))
CURRENT_SAVINGS_BALANCE = "current_savings_balance"
FRED_API_KEY = "fred_api_key"
CLEAR_FRED_API_KEY = "clear_fred_api_key"
EOD_API_KEY = "eod_api_key"
CLEAR_EOD_API_KEY = "clear_eod_api_key"
PLAN_NAME = "name"
RETURN_PLAN = "return_plan"
CLAIM_AGE_YEARS = "claim_age_years"
CLAIM_AGE_MONTHS = "claim_age_months"

PENSION_NONE = "none"
PENSION_CALSTRS_2_AT_62 = "calstrs_2_at_62"
PENSION_LABEL = "Pension"
PENSION_NONE_LABEL = "None"
PENSION_CALSTRS_2_AT_62_LABEL = "CalSTRS 2% at 62"
MONTH_OF_BIRTH_LABEL = "Month of Birth"
RESIDENCE_STATE_NONE = "none"
RESIDENCE_STATE_NONE_LABEL = "No income-tax state"
RESIDENCE_STATE_REQUEST_ISSUE_URL = (
    "https://github.com/chriskelly/LifeFinances/issues/200"
)
RESIDENCE_STATE_REQUEST_LINK_TEXT = "Request your state (#200)"
SS_EARNINGS_FILE = "statement"


class HouseholdForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    person1_birth_month: int
    person1_birth_year: int
    person1_max_age_years: int
    filing_status: FilingStatus
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal = Decimal("0.80")
    social_security_trust_factor: Decimal = Decimal(1)
    has_partner: bool = False
    person2_birth_month: int | None = None
    person2_birth_year: int | None = None
    person2_max_age_years: int | None = None

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        data["person1"].update(
            {
                "birth_month": self.person1_birth_month,
                "birth_year": self.person1_birth_year,
                "max_age_years": self.person1_max_age_years,
            }
        )
        if self.has_partner:
            existing2 = data.get("person2")
            if existing2 is None:
                existing2 = PersonHousehold(
                    birth_month=self.person2_birth_month or 1,
                    birth_year=self.person2_birth_year or 0,
                    max_age_years=self.person2_max_age_years or 1,
                ).model_dump()
            existing2.update(
                {
                    "birth_month": self.person2_birth_month,
                    "birth_year": self.person2_birth_year,
                    "max_age_years": self.person2_max_age_years,
                }
            )
            data["person2"] = existing2
        else:
            data["person2"] = None
        data["filing_status"] = self.filing_status
        if self.residence_state is not None:
            data["residence_state"] = (
                None
                if self.residence_state in ("", RESIDENCE_STATE_NONE)
                else self.residence_state
            )
        data["ss_pension_taxable_fraction"] = self.ss_pension_taxable_fraction
        data["social_security_trust_factor"] = self.social_security_trust_factor
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})


class PortfolioForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    current_savings_balance: Decimal

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.portfolio.model_dump()
        data["current_savings_balance"] = self.current_savings_balance
        portfolio = Portfolio.model_validate(data)
        return plan.model_copy(update={"portfolio": portfolio})


def _apply_api_key(
    settings: AppSettings,
    *,
    field: str,
    value: str | None,
    clear: bool,
) -> AppSettings:
    if clear:
        return settings.model_copy(update={field: None})
    if value and value.strip():
        return settings.model_copy(update={field: value.strip()})
    return settings


class AppSettingsForm(BaseModel):
    """Flat transport DTO for local app settings."""

    fred_api_key: str | None = None
    clear_fred_api_key: bool = False
    eod_api_key: str | None = None
    clear_eod_api_key: bool = False

    def apply_to(self, settings: AppSettings) -> AppSettings:
        updated = _apply_api_key(
            settings,
            field="fred_api_key",
            value=self.fred_api_key,
            clear=self.clear_fred_api_key,
        )
        return _apply_api_key(
            updated,
            field="eod_api_key",
            value=self.eod_api_key,
            clear=self.clear_eod_api_key,
        )


def _job_from_row(row: list[tuple[str, str]], *, today: date) -> Job:
    pension: dict[str, object] | None = None
    if boundaries.row_scalar(row, "pension", PENSION_NONE) == PENSION_CALSTRS_2_AT_62:
        pension = {
            "service_start": boundaries.row_boundary(
                row, "pension_service_start", today=today
            ),
            "claim": boundaries.row_boundary(row, "pension_claim", today=today),
            "age_factor_table": age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS),
            "final_comp_averaging_months": int(
                boundaries.row_scalar(row, "pension_averaging_months", "36")
            ),
            "trust_factor": parse_percent(
                boundaries.row_scalar(row, "pension_trust_factor", "100%")
            ),
            "benefit_real_growth_rate": parse_percent(
                boundaries.row_scalar(row, "pension_growth", "0%")
            ),
        }
    sabbaticals = [
        {
            "start": boundaries.row_boundary(sab, "start", today=today),
            "end": boundaries.row_boundary(sab, "end", today=today),
            "remaining_fraction": parse_percent(
                boundaries.row_scalar(sab, "remaining_fraction", "0%")
            ),
        }
        for sab in boundaries.sub_rows(row, "sabbaticals")
    ]
    return Job.model_validate(
        {
            "label": boundaries.row_scalar(row, "label") or None,
            "annual_income": parse_usd(
                boundaries.row_scalar(row, "annual_income", "0")
            ),
            "annual_tax_deferred": parse_usd(
                boundaries.row_scalar(row, "annual_tax_deferred", "0")
            ),
            "annual_raise": parse_percent(
                boundaries.row_scalar(row, "annual_raise", "0%")
            ),
            "start": boundaries.row_boundary(row, "start", today=today),
            "end": boundaries.row_boundary(row, "end", today=today),
            "social_security_eligible": boundaries.row_scalar(
                row, "social_security_eligible"
            )
            in _TRUE,
            "sabbaticals": sabbaticals,
            "pension": pension,
        }
    )


class JobsForm:
    def __init__(self, *, person: PersonId, jobs: list[Job]) -> None:
        self.person = person
        self.jobs = jobs

    @classmethod
    def from_form(cls, form: FormData, *, person: PersonId, today: date) -> JobsForm:
        rows = boundaries.collect_indexed_rows(form, JOBS_PREFIX)
        return cls(
            person=person, jobs=[_job_from_row(row, today=today) for row in rows]
        )

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        if data.get(self.person) is None:
            raise ValueError("Cannot edit jobs for a partner who is not on the plan")
        data[self.person]["jobs"] = [job.model_dump() for job in self.jobs]
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})


def _stream_from_row(row: list[tuple[str, str]], *, today: date) -> TimedStream:
    return TimedStream.model_validate(
        {
            "label": boundaries.row_scalar(row, "label") or None,
            "monthly_amount": parse_usd(
                boundaries.row_scalar(row, "monthly_amount", "0")
            ),
            "start": boundaries.row_boundary(row, "start", today=today),
            "end": boundaries.row_boundary(row, "end", today=today),
            "is_nominal": boundaries.row_scalar(row, "is_nominal") in _TRUE,
            "annual_growth_rate": parse_percent(
                boundaries.row_scalar(row, "annual_growth_rate", "0%")
            ),
        }
    )


class ManualIncomeForm:
    def __init__(self, *, streams: list[TimedStream]) -> None:
        self.streams = streams

    @classmethod
    def from_form(cls, form: FormData, *, today: date) -> ManualIncomeForm:
        rows = boundaries.collect_indexed_rows(form, STREAMS_PREFIX)
        return cls(streams=[_stream_from_row(row, today=today) for row in rows])

    def apply_to(self, plan: Plan) -> Plan:
        return plan.model_copy(update={"manual_income_streams": self.streams})


class SocialSecurityForm(BaseModel):
    """Flat transport DTO. Bounds live on core.social_security."""

    person: PersonId
    claim_age_years: int
    claim_age_months: int = 0

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        if data.get(self.person) is None:
            raise ValueError(
                "Cannot edit Social Security for a partner who is not on the plan"
            )
        data[self.person]["social_security"]["claim_age_months"] = (
            self.claim_age_years * 12 + self.claim_age_months
        )
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})
