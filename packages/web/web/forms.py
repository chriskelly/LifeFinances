from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Literal, get_args

from core.job import AgeFactor, FormulaPension, Job
from core.models import RISK_TOLERANCE_NUM_VALUES as _RISK_TOLERANCE_NUM_VALUES
from core.models import (
    AdvancedConfig,
    AppSettings,
    BondPresetBase,
    FilingStatus,
    Household,
    InflationConfig,
    PersonHousehold,
    Plan,
    PlanningPreset,
    PlanningReturnsConfig,
    Portfolio,
    RiskConfig,
    SamplingConfig,
    StockPresetBase,
    normalize_percentiles,
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
from web.currency import format_usd, parse_usd
from web.percent import parse_percent

JOBS_PREFIX = "jobs"
STREAMS_PREFIX = "streams"
ESSENTIAL_PREFIX = "essential"
DISCRETIONARY_PREFIX = "discretionary"
LEGACY_TARGET = "legacy_target"
LEGACY_TARGET_HELP = "Target at the plan horizon, in today's dollars."
RISK_TOLERANCE_AT_20 = "risk_tolerance_at_20"
DELTA_AT_MAX_AGE = "delta_at_max_age"
LEGACY_DELTA_FROM_AT_20 = "legacy_delta_from_at_20"
TIME_PREFERENCE = "time_preference"
ADDITIONAL_ANNUAL_SPENDING_TILT = "additional_annual_spending_tilt"
INFLATION_MODE = "inflation_mode"
INFLATION_MANUAL_ANNUAL_RATE = "inflation_manual_annual_rate"
PLANNING_PRESET = "planning_preset"
FIXED_EQUITY_PREMIUM = "fixed_equity_premium"
CUSTOM_STOCKS_BASE = "custom_stocks_base"
CUSTOM_BONDS_BASE = "custom_bonds_base"
CUSTOM_STOCKS_DELTA = "custom_stocks_delta"
CUSTOM_BONDS_DELTA = "custom_bonds_delta"
EXPECTED_ANNUAL_RETURN_STOCKS = "expected_annual_return_stocks"
EXPECTED_ANNUAL_RETURN_BONDS = "expected_annual_return_bonds"
STOCK_VOLATILITY_SCALE = "stock_volatility_scale"
BLOCK_SIZE_MONTHS = "block_size_months"
NUM_RUNS = "num_runs"
STAGGER_RUN_STARTS = "stagger_run_starts"
SAMPLING_SEED = "seed"
PERCENTILES = "percentiles"
PERCENTILES_WEALTH_MAPPING_HELP = (
    "Wealth composition Low, Middle, and High use the first, middle, "
    "and last configured percentiles."
)
FIXED_EQUITY_PREMIUM_FORM_DEFAULT = Decimal("0.03")
CUSTOM_STOCKS_BASE_FORM_DEFAULT: StockPresetBase = "regression_prediction"
CUSTOM_BONDS_BASE_FORM_DEFAULT: BondPresetBase = "twenty_year_tips_yield"
INFLATION_MODES: tuple[Literal["suggested", "manual"], ...] = (
    "suggested",
    "manual",
)
INFLATION_MODE_LABELS = {
    "suggested": "Suggested",
    "manual": "Manual",
}
PLANNING_PRESETS: tuple[PlanningPreset, ...] = get_args(PlanningPreset)
PLANNING_PRESET_LABELS = {
    "regression_prediction": "Regression prediction + 20-year TIPS",
    "conservative_estimate": "Conservative estimate + 20-year TIPS",
    "one_over_cape": "1/CAPE + 20-year TIPS",
    "historical": "Historical",
    "fixed_equity_premium": "Fixed equity premium",
    "custom": "Custom",
    "fixed": "Fixed",
}
STOCK_PRESET_BASES: tuple[StockPresetBase, ...] = get_args(StockPresetBase)
STOCK_PRESET_BASE_LABELS = {
    "regression_prediction": "Regression prediction",
    "conservative_estimate": "Conservative estimate",
    "one_over_cape": "1/CAPE",
    "historical": "Historical",
}
BOND_PRESET_BASES: tuple[BondPresetBase, ...] = get_args(BondPresetBase)
BOND_PRESET_BASE_LABELS = {
    "twenty_year_tips_yield": "20-year TIPS yield",
    "historical": "Historical",
}
# Re-export for Jinja templates (`forms.RISK_TOLERANCE_NUM_VALUES`).
RISK_TOLERANCE_NUM_VALUES = _RISK_TOLERANCE_NUM_VALUES
PERCENT_SLIDER_MIN = "-5"
PERCENT_SLIDER_MAX = "5"
PERCENT_SLIDER_STEP = "0.25"
STREAM_LABEL = "label"
STREAM_MONTHLY_AMOUNT = "monthly_amount"
STREAM_IS_NOMINAL = "is_nominal"
STREAM_ANNUAL_GROWTH_RATE = "annual_growth_rate"
STREAM_START = "start"
STREAM_END = "end"
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
PENSION_CUSTOM = "custom"
PENSION_LABEL = "Pension"
PENSION_NONE_LABEL = "None"
PENSION_CALSTRS_2_AT_62_LABEL = "CalSTRS 2% at 62"
PENSION_CUSTOM_LABEL = "Custom"
PENSION_AVERAGING_MONTHS_DEFAULT = int(
    FormulaPension.model_fields["final_comp_averaging_months"].default
)
PENSION_REQUEST_ISSUE_URL = "https://github.com/chriskelly/LifeFinances/issues/197"
PENSION_REQUEST_LINK_TEXT = "More pension options (#197)"
PENSION_REQUEST_LINK_TITLE = "Vote for a richer pension editor"
EXISTING_INDEX = "existing_index"
PENSION_AGE_FACTOR_TABLE = "pension_age_factor_table"
INVALID_AGE_FACTOR_TABLE_MESSAGE = "Custom pension table is missing or invalid"
INVALID_AVERAGING_MONTHS_MESSAGE = "Enter averaging months as a whole number"
REMOVE_PARTNER_CONFIRM = (
    "Remove partner? Their jobs and Social Security earnings will be deleted."
)
MONTH_OF_BIRTH_LABEL = "Month of Birth"
RESIDENCE_STATE_NONE = "none"
RESIDENCE_STATE_NONE_LABEL = "No income-tax state"
RESIDENCE_STATE_REQUEST_ISSUE_URL = (
    "https://github.com/chriskelly/LifeFinances/issues/200"
)
RESIDENCE_STATE_REQUEST_LINK_TEXT = "Request your state (#200)"
SS_EARNINGS_FILE = "statement"


def parse_filing_status(raw: str) -> FilingStatus:
    if raw == "single" or raw == "married_filing_jointly":
        return raw
    raise ValueError(f"unknown filing status: {raw!r}")


def parse_residence_state(raw: str) -> str | None:
    """Map a residence-state selection to a stored value, or `None` for no state tax.

    Anything outside `TAX_MODELED_STATES` is rejected rather than stored, because
    the tax layer silently treats an unknown state as zero state income tax.
    """
    if raw == RESIDENCE_STATE_NONE:
        return None
    if raw in TAX_MODELED_STATES:
        return raw
    raise ValueError(f"{raw!r} is not a state we model income tax for")


def people_choices(plan: Plan) -> list[tuple[str, str, PersonHousehold]]:
    people: list[tuple[str, str, PersonHousehold]] = [
        ("person1", "You", plan.household.person1)
    ]
    if plan.household.person2 is not None:
        people.append(("person2", "Partner", plan.household.person2))
    return people


def calstrs_age_factor_table() -> list[AgeFactor]:
    return age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS)


def is_calstrs_pension(pension: FormulaPension | None) -> bool:
    if pension is None:
        return False
    return pension.age_factor_table == calstrs_age_factor_table()


def _usd_display_matches(*, submitted: str, amount: Decimal) -> bool:
    return submitted.strip() == format_usd(amount)


def _resolve_previous[T](
    row: list[tuple[str, str]],
    *,
    existing: list[T],
    claimed: set[int],
    amount_of: Callable[[T], Decimal],
    amount_field: str,
) -> T | None:
    """Map a submitted row to an existing item without trusting a stale index.

    `EXISTING_INDEX` is only accepted when its USD display still matches the
    submitted amount. Otherwise (or when the index is out of range), fall back
    to a unique display match among unclaimed items. This keeps cent-preserving
    `parse_usd(..., previous=)` correct after delete-under-`hx-swap=none`.
    """
    submitted = boundaries.row_scalar(row, amount_field, "0")
    raw_index = boundaries.row_scalar(row, EXISTING_INDEX).strip()
    if raw_index:
        index = int(raw_index)
        if 0 <= index < len(existing) and index not in claimed:
            candidate = existing[index]
            if _usd_display_matches(submitted=submitted, amount=amount_of(candidate)):
                claimed.add(index)
                return candidate
    matches = [
        i
        for i, item in enumerate(existing)
        if i not in claimed
        and _usd_display_matches(submitted=submitted, amount=amount_of(item))
    ]
    if len(matches) == 1:
        claimed.add(matches[0])
        return existing[matches[0]]
    return None


def encode_age_factor_table(table: list[AgeFactor]) -> str:
    return json.dumps([factor.model_dump(mode="json") for factor in table])


def decode_age_factor_table(raw: str) -> list[AgeFactor]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(INVALID_AGE_FACTOR_TABLE_MESSAGE) from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError(INVALID_AGE_FACTOR_TABLE_MESSAGE)
    try:
        return [AgeFactor.model_validate(item) for item in payload]
    except (TypeError, ValueError) as exc:
        raise ValueError(INVALID_AGE_FACTOR_TABLE_MESSAGE) from exc


def _parse_averaging_months(raw: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(INVALID_AVERAGING_MONTHS_MESSAGE) from exc


def _custom_age_factor_table(
    row: list[tuple[str, str]], *, previous: Job | None
) -> list[AgeFactor]:
    encoded = boundaries.row_scalar(row, PENSION_AGE_FACTOR_TABLE)
    if encoded.strip():
        return decode_age_factor_table(encoded)
    if previous is not None and previous.pension is not None:
        return previous.pension.age_factor_table
    raise ValueError("Custom pension is no longer available; choose CalSTRS or None")


def _pension_fields_from_row(
    row: list[tuple[str, str]],
    *,
    today: date,
    age_factor_table: list[AgeFactor],
) -> dict[str, object]:
    return {
        "service_start": boundaries.row_boundary(
            row, "pension_service_start", today=today
        ),
        "claim": boundaries.row_boundary(row, "pension_claim", today=today),
        "age_factor_table": age_factor_table,
        "final_comp_averaging_months": _parse_averaging_months(
            boundaries.row_scalar(
                row,
                "pension_averaging_months",
                str(PENSION_AVERAGING_MONTHS_DEFAULT),
            )
        ),
        "trust_factor": parse_percent(
            boundaries.row_scalar(row, "pension_trust_factor", "100%")
        ),
        "benefit_real_growth_rate": parse_percent(
            boundaries.row_scalar(row, "pension_growth", "0%")
        ),
    }


def _job_from_row(
    row: list[tuple[str, str]], *, today: date, previous: Job | None = None
) -> Job:
    pension_choice = boundaries.row_scalar(row, "pension", PENSION_NONE)
    pension: dict[str, object] | None = None
    if pension_choice == PENSION_CALSTRS_2_AT_62:
        pension = _pension_fields_from_row(
            row, today=today, age_factor_table=calstrs_age_factor_table()
        )
    elif pension_choice == PENSION_CUSTOM:
        pension = _pension_fields_from_row(
            row,
            today=today,
            age_factor_table=_custom_age_factor_table(row, previous=previous),
        )
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
                boundaries.row_scalar(row, "annual_income", "0"),
                previous=previous.annual_income if previous else None,
            ),
            "annual_tax_deferred": parse_usd(
                boundaries.row_scalar(row, "annual_tax_deferred", "0"),
                previous=previous.annual_tax_deferred if previous else None,
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
    def from_form(
        cls,
        form: FormData,
        *,
        person: PersonId,
        today: date,
        existing_jobs: list[Job],
    ) -> JobsForm:
        rows = boundaries.collect_indexed_rows(form, JOBS_PREFIX)
        jobs: list[Job] = []
        claimed: set[int] = set()
        for row in rows:
            previous = _resolve_previous(
                row,
                existing=existing_jobs,
                claimed=claimed,
                amount_of=lambda job: job.annual_income,
                amount_field="annual_income",
            )
            jobs.append(_job_from_row(row, today=today, previous=previous))
        return cls(person=person, jobs=jobs)

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        if data.get(self.person) is None:
            raise ValueError("Cannot edit jobs for a partner who is not on the plan")
        data[self.person]["jobs"] = [job.model_dump() for job in self.jobs]
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})


class HouseholdForm(BaseModel):
    person1_birth_month: int
    person1_birth_year: int
    person1_max_age_years: int
    filing_status: FilingStatus
    # `None` means "absent from the submission", so the stored value is left
    # alone. Clearing residence state is the explicit RESIDENCE_STATE_NONE
    # selection, not an omitted field.
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal | None = None
    social_security_trust_factor: Decimal | None = None
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
            if (
                self.person2_birth_month is None
                or self.person2_birth_year is None
                or self.person2_max_age_years is None
            ):
                raise ValueError("Partner requires birth month, year, and max age")
            existing2 = data.get("person2")
            if existing2 is None:
                existing2 = PersonHousehold(
                    birth_month=self.person2_birth_month,
                    birth_year=self.person2_birth_year,
                    max_age_years=self.person2_max_age_years,
                ).model_dump()
            else:
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
            data["residence_state"] = parse_residence_state(self.residence_state)
        if self.ss_pension_taxable_fraction is not None:
            data["ss_pension_taxable_fraction"] = self.ss_pension_taxable_fraction
        if self.social_security_trust_factor is not None:
            data["social_security_trust_factor"] = self.social_security_trust_factor
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})


class PortfolioForm(BaseModel):
    current_savings_balance: Decimal

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.portfolio.model_dump()
        data["current_savings_balance"] = self.current_savings_balance
        portfolio = Portfolio.model_validate(data)
        return plan.model_copy(update={"portfolio": portfolio})


class RiskForm(BaseModel):
    risk_tolerance_at_20: Decimal
    delta_at_max_age: Decimal
    legacy_delta_from_at_20: Decimal
    time_preference: Decimal
    additional_annual_spending_tilt: Decimal

    def apply_to(self, plan: Plan) -> Plan:
        risk = RiskConfig.model_validate(self.model_dump())
        return plan.model_copy(update={"risk": risk})


class MarketAssumptionsForm(BaseModel):
    inflation_mode: Literal["suggested", "manual"]
    inflation_manual_annual_rate: Decimal | None = None
    planning_preset: PlanningPreset
    fixed_equity_premium: Decimal | None = None
    custom_stocks_base: StockPresetBase | None = None
    custom_bonds_base: BondPresetBase | None = None
    custom_stocks_delta: Decimal | None = None
    custom_bonds_delta: Decimal | None = None
    expected_annual_return_stocks: Decimal | None = None
    expected_annual_return_bonds: Decimal | None = None
    stock_volatility_scale: Decimal | None = None

    def apply_to(self, plan: Plan) -> Plan:
        inflation_data = plan.inflation.model_dump()
        inflation_data["mode"] = self.inflation_mode
        if self.inflation_manual_annual_rate is not None:
            inflation_data["manual_annual_rate"] = self.inflation_manual_annual_rate

        returns_data = plan.planning_returns.model_dump()
        returns_data["preset"] = self.planning_preset
        for field in (
            "fixed_equity_premium",
            "custom_stocks_base",
            "custom_bonds_base",
            "custom_stocks_delta",
            "custom_bonds_delta",
            "expected_annual_return_stocks",
            "expected_annual_return_bonds",
            "stock_volatility_scale",
        ):
            value = getattr(self, field)
            if value is not None:
                returns_data[field] = value

        return plan.model_copy(
            update={
                "inflation": InflationConfig.model_validate(inflation_data),
                "planning_returns": PlanningReturnsConfig.model_validate(returns_data),
            }
        )


def parse_percentiles_field(raw: str) -> list[int]:
    tokens = [token.strip() for token in raw.split(",")]
    if not tokens or any(not token for token in tokens):
        raise ValueError("Enter one or more comma-separated percentiles")
    try:
        parsed = [int(token) for token in tokens]
    except ValueError as exc:
        raise ValueError("Percentiles must be whole numbers") from exc
    return normalize_percentiles(parsed)


class SimulationDetailsForm(BaseModel):
    block_size_months: int
    num_runs: int
    stagger_run_starts: bool
    seed: int
    percentiles: list[int]

    def apply_to(self, plan: Plan) -> Plan:
        sampling = SamplingConfig(
            block_size_months=self.block_size_months,
            num_runs=self.num_runs,
            stagger_run_starts=self.stagger_run_starts,
            seed=self.seed,
        )
        advanced = AdvancedConfig(percentiles=self.percentiles)
        return plan.model_copy(update={"sampling": sampling, "advanced": advanced})


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


def _stream_from_row(
    row: list[tuple[str, str]],
    *,
    today: date,
    previous: TimedStream | None = None,
) -> TimedStream:
    return TimedStream.model_validate(
        {
            "label": boundaries.row_scalar(row, STREAM_LABEL) or None,
            "monthly_amount": parse_usd(
                boundaries.row_scalar(row, STREAM_MONTHLY_AMOUNT, "0"),
                previous=previous.monthly_amount if previous else None,
            ),
            "start": boundaries.row_boundary(row, STREAM_START, today=today),
            "end": boundaries.row_boundary(row, STREAM_END, today=today),
            "is_nominal": boundaries.row_scalar(row, STREAM_IS_NOMINAL) in _TRUE,
            "annual_growth_rate": parse_percent(
                boundaries.row_scalar(row, STREAM_ANNUAL_GROWTH_RATE, "0%")
            ),
        }
    )


def _streams_from_form(
    form: FormData,
    *,
    prefix: str,
    today: date,
    existing: list[TimedStream],
) -> list[TimedStream]:
    rows = boundaries.collect_indexed_rows(form, prefix)
    streams: list[TimedStream] = []
    claimed: set[int] = set()
    for row in rows:
        previous = _resolve_previous(
            row,
            existing=existing,
            claimed=claimed,
            amount_of=lambda stream: stream.monthly_amount,
            amount_field=STREAM_MONTHLY_AMOUNT,
        )
        streams.append(_stream_from_row(row, today=today, previous=previous))
    return streams


class ManualIncomeForm:
    def __init__(self, *, streams: list[TimedStream]) -> None:
        self.streams = streams

    @classmethod
    def from_form(
        cls,
        form: FormData,
        *,
        today: date,
        existing_streams: list[TimedStream],
    ) -> ManualIncomeForm:
        return cls(
            streams=_streams_from_form(
                form,
                prefix=STREAMS_PREFIX,
                today=today,
                existing=existing_streams,
            )
        )

    def apply_to(self, plan: Plan) -> Plan:
        return plan.model_copy(update={"manual_income_streams": self.streams})


class SpendingGoalsForm:
    def __init__(
        self,
        *,
        essential: list[TimedStream],
        discretionary: list[TimedStream],
        legacy_target: Decimal,
    ) -> None:
        self.essential = essential
        self.discretionary = discretionary
        self.legacy_target = legacy_target

    @classmethod
    def from_form(
        cls,
        form: FormData,
        *,
        today: date,
        existing_essential: list[TimedStream],
        existing_discretionary: list[TimedStream],
        existing_legacy_target: Decimal,
    ) -> SpendingGoalsForm:
        raw_legacy = form.get(LEGACY_TARGET, "")
        if not isinstance(raw_legacy, str):
            raise ValueError("Legacy target must be text")
        legacy_target = parse_usd(raw_legacy, previous=existing_legacy_target)
        return cls(
            essential=_streams_from_form(
                form,
                prefix=ESSENTIAL_PREFIX,
                today=today,
                existing=existing_essential,
            ),
            discretionary=_streams_from_form(
                form,
                prefix=DISCRETIONARY_PREFIX,
                today=today,
                existing=existing_discretionary,
            ),
            legacy_target=legacy_target,
        )

    def apply_to(self, plan: Plan) -> Plan:
        return plan.model_copy(
            update={
                "extra_essential_spending": self.essential,
                "extra_discretionary_spending": self.discretionary,
                "legacy_target": self.legacy_target,
            }
        )


class SocialSecurityForm(BaseModel):
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
