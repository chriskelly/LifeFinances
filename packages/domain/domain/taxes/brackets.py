from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from domain.statutory.taxes import Bracket

_CENTS = Decimal("0.01")


def cumulative_prior_at_bracket_index(
    brackets: tuple[Bracket, ...], index: int
) -> Decimal:
    """Tax owed at the top of the prior bracket (entering ``index``).

    Derived from rate and cap columns only; quantize to cents at the boundary.
    """
    if index == 0:
        return Decimal("0.00")
    cumulative = Decimal(0)
    lower_cap = Decimal(0)
    for j in range(index):
        rate, cap, _ = brackets[j]
        cumulative += rate * (cap - lower_cap)
        lower_cap = cap
    return cumulative.quantize(_CENTS, rounding=ROUND_HALF_UP)


def progressive_tax(brackets: tuple[Bracket, ...], taxable_income: Decimal) -> Decimal:
    """Tax owed (positive) on `taxable_income` in dollars."""
    if taxable_income <= 0:
        return Decimal("0.00")
    previous_cap = Decimal(0)
    for rate, cap, cumulative_prior in brackets:
        if taxable_income < cap:
            return (cumulative_prior + rate * (taxable_income - previous_cap)).quantize(
                _CENTS, rounding=ROUND_HALF_UP
            )
        previous_cap = cap
    raise ValueError("annual taxable income exceeds the highest tax bracket")


def annual_income_tax(
    *,
    brackets: tuple[Bracket, ...],
    standard_deduction: Decimal,
    annual_income: Decimal,
) -> Decimal:
    taxable = annual_income - standard_deduction
    if taxable <= 0:
        return Decimal("0.00")
    return progressive_tax(brackets, taxable)
