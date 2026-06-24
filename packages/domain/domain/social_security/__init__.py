from __future__ import annotations

from decimal import Decimal

from core.models import PersonHousehold, Plan
from core.streams import PersonAgeBoundary, PersonId
from core.timeline import Timeline
from pydantic import BaseModel, computed_field

from domain.job_income import JobIncomeProjection
from domain.social_security.benefits import (
    calculate_aime,
    calculate_pia,
    claim_age_multiplier,
)
from domain.social_security.earnings import (
    group_monthly_earnings_by_year,
    indexed_annual_earnings,
)

_CENTS = Decimal("0.01")


class PersonSocialSecurity(BaseModel):
    """Projected Social Security for one person."""

    own_benefit: list[Decimal]
    spousal_alternative: list[Decimal]
    max_benefit: list[Decimal]

    @computed_field
    @property
    def spousal_top_up(self) -> list[Decimal]:
        return [
            benefit - own
            for own, benefit in zip(self.own_benefit, self.max_benefit, strict=True)
        ]


class SocialSecurityProjection(BaseModel):
    person1: PersonSocialSecurity
    person2: PersonSocialSecurity
    total: list[Decimal]


class _PersonInputs(BaseModel):
    pia: Decimal
    effective_pia: Decimal
    claim_multiplier: Decimal
    claim_start_index: int


def _person_inputs(
    *,
    person: PersonHousehold,
    person_id: PersonId,
    timeline: Timeline,
    future_ss_covered: list[Decimal],
    trust_factor: Decimal,
) -> _PersonInputs:
    future_by_year = group_monthly_earnings_by_year(future_ss_covered, timeline)
    earnings = indexed_annual_earnings(
        historical_earnings=person.social_security.earnings_record,
        future_real_earnings_by_year=future_by_year,
        today_year=timeline.today.year,
    )
    pia = calculate_pia(calculate_aime(earnings)) if earnings else Decimal("0.00")
    effective_pia = (pia * trust_factor).quantize(_CENTS)
    claim_multiplier = claim_age_multiplier(person.social_security.claim_age_months)
    claim_start_index = timeline.index_of(
        PersonAgeBoundary(
            person=person_id,
            age_months=person.social_security.claim_age_months,
        )
    )
    return _PersonInputs(
        pia=pia,
        effective_pia=effective_pia,
        claim_multiplier=claim_multiplier,
        claim_start_index=claim_start_index,
    )


def _own_series(inputs: _PersonInputs, horizon: int) -> list[Decimal]:
    series = [Decimal("0.00")] * horizon
    monthly = (inputs.effective_pia * inputs.claim_multiplier).quantize(_CENTS)
    low = max(inputs.claim_start_index, 0)
    for month_index in range(low, horizon):
        series[month_index] = monthly
    return series


def _person_projection(
    own_benefit: list[Decimal],
    spousal_alternative: list[Decimal],
) -> PersonSocialSecurity:
    max_benefit = [
        max(own, spousal)
        for own, spousal in zip(own_benefit, spousal_alternative, strict=True)
    ]
    return PersonSocialSecurity(
        own_benefit=own_benefit,
        spousal_alternative=spousal_alternative,
        max_benefit=max_benefit,
    )


def project_social_security(
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
) -> SocialSecurityProjection:
    horizon = timeline.horizon_months
    trust_factor = plan.household.social_security_trust_factor
    person1_inputs = _person_inputs(
        person=plan.household.person1,
        person_id="person1",
        timeline=timeline,
        future_ss_covered=job_income.person1.ss_covered_gross,
        trust_factor=trust_factor,
    )
    person2_inputs = _person_inputs(
        person=plan.household.person2,
        person_id="person2",
        timeline=timeline,
        future_ss_covered=job_income.person2.ss_covered_gross,
        trust_factor=trust_factor,
    )
    person1 = _person_projection(
        _own_series(person1_inputs, horizon), [Decimal("0.00")] * horizon
    )
    person2 = _person_projection(
        _own_series(person2_inputs, horizon), [Decimal("0.00")] * horizon
    )
    return SocialSecurityProjection(
        person1=person1,
        person2=person2,
        total=[
            a + b for a, b in zip(person1.max_benefit, person2.max_benefit, strict=True)
        ],
    )
