from __future__ import annotations

from decimal import Decimal

from core.social_security import FULL_RETIREMENT_AGE_MONTHS

from domain.statutory.social_security import CURRENT_BEND_POINTS, PIA_RATES

_CENTS = Decimal("0.01")


def calculate_aime(indexed_annual_earnings: list[Decimal]) -> Decimal:
    """Average indexed monthly earnings from highest 35 annual earnings years."""
    top_years = sorted(indexed_annual_earnings, reverse=True)[:35]
    if len(top_years) < 35:
        top_years = [*top_years, *([Decimal("0")] * (35 - len(top_years)))]
    return sum(top_years) / Decimal(35 * 12)


def calculate_pia(aime: Decimal) -> Decimal:
    """Primary Insurance Amount using the standard 90/32/15 formula."""
    first_bend, second_bend = CURRENT_BEND_POINTS
    rate1, rate2, rate3 = PIA_RATES
    first_slice = min(aime, first_bend)
    second_slice = min(max(aime - first_bend, Decimal("0")), second_bend - first_bend)
    third_slice = max(aime - second_bend, Decimal("0"))
    return (first_slice * rate1 + second_slice * rate2 + third_slice * rate3).quantize(
        _CENTS
    )


def claim_age_multiplier(claim_age_months: int) -> Decimal:
    """Monthly early/delayed retirement multiplier relative to FRA 67."""
    if claim_age_months < FULL_RETIREMENT_AGE_MONTHS:
        months_early = FULL_RETIREMENT_AGE_MONTHS - claim_age_months
        first_36 = min(months_early, 36)
        additional = max(months_early - 36, 0)
        reduction = Decimal(first_36) * Decimal(5) / Decimal(900) + Decimal(
            additional
        ) * Decimal(5) / Decimal(1200)
        return Decimal("1") - reduction
    months_delayed = claim_age_months - FULL_RETIREMENT_AGE_MONTHS
    return Decimal("1") + Decimal(months_delayed) * Decimal(2) / Decimal(300)
