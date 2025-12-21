"""Tax Rates and Functions

This module contains the constants related to taxes across all supported states.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app import util
from app.data.constants import INTERVALS_PER_YEAR
from app.data.taxes import *  # pylint: disable=wildcard-import
from app.models.config import User
from app.util import max_earnings_extrapolator

# pylint: disable=used-before-assignment
if TYPE_CHECKING:
    from app.models.controllers.job_income import Controller as JobIncomeController
    from app.models.financial.state import State
    from app.models.financial.state_change import Income


@dataclass
class Taxes:
    """Taxes paid in a given interval

    Attributes:
        income (float): income taxes on job income or social security
        medicare (float): medicare taxes as part of FICA
        social_security (float): social security taxes as part of FICA
        portfolio (float): taxes on portfolio income
        sum (float): sum of all taxes
    """

    income: float
    medicare: float
    social_security: float
    portfolio: float
    sum: float = field(init=False)

    def __post_init__(self):
        self.sum = float(
            self.income + self.medicare + self.social_security + self.portfolio
        )


def calc_taxes(
    total_income: Income,
    job_income_controller: JobIncomeController,
    state: State,
    portfolio_return: float,
) -> Taxes:
    """Calculates taxes for a given interval

    Returns:
        Taxes: Attributes: income, medicare, social_security, portfolio
    """
    taxable_income = job_income_controller.get_taxable_income(state.interval_idx)
    job_income_tax = _calc_income_taxes(interval_income=taxable_income, state=state)
    pension_income_tax = (1 - DISCOUNT_ON_PENSION_TAX) * _calc_income_taxes(
        interval_income=total_income.social_security_user
        + total_income.social_security_partner
        + total_income.pension,
        state=state,
    )
    return Taxes(
        income=job_income_tax + pension_income_tax,
        medicare=-total_income.job_income * MEDICARE_TAX_RATE,
        social_security=_social_security_tax(job_income_controller, state),
        # Assumes user tax-loss harvestes, so tax is always has opposite sign of return
        # There is technically an annual limit to harvesting, but losses carry over,
        # so for simplicity we assume it is always harvested the year it is incurred.
        portfolio=-portfolio_return * state.user.portfolio.tax_rate,
    )


def _calc_income_taxes(interval_income: float, state: State) -> float:
    """Combines federal and state taxes on non-tax-deferred income

    Assumes that tax brackets are updated and that future years
    will have the same tax brackets, just adjusted for inflation.

    Args:
        interval_income (float): income in quarterly amount
        state (State): current state

    Returns:
        (float): federal and state tax burden for that quarter
    """
    if interval_income == 0.0:
        return 0  # avoid bracket math if no income

    inflation = state.inflation
    tax_rules = _TaxRules(state.user)

    adj_income = (
        INTERVALS_PER_YEAR * interval_income / inflation
    )  # convert income to yearly and adjust for inflation

    fed_taxes = _bracket_math(
        brackets=tax_rules.federal_bracket_rates,
        yearly_income=util.constrain(
            adj_income - tax_rules.federal_standard_deduction, low=0
        ),
    )
    if tax_rules.state_bracket_rates is None:
        state_taxes = 0
    else:
        state_taxes = _bracket_math(
            brackets=tax_rules.state_bracket_rates,
            yearly_income=util.constrain(
                adj_income - tax_rules.state_standard_deduction, low=0
            ),
        )
    return (fed_taxes + state_taxes) / INTERVALS_PER_YEAR


class _TaxRules:
    """Tax rules for a given user

    Args:
        user (User): current user

    Attributes:
        federal_bracket_rates (list): federal brackets for income tax in format
            [rate,highest dollar that rate applies to,sum of tax owed in previous brackets]
        state_bracket_rates (list): state brackets for income tax in format
            [rate,highest dollar that rate applies to,sum of tax owed in previous brackets]
        federal_standard_deduction (float): federal standard deduction
        state_standard_deduction (float): state standard deduction
    """

    def __init__(self, user: User):
        married = bool(user.partner)
        residence_state = user.state
        if residence_state is None:
            self.state_bracket_rates = None
            self.state_standard_deduction = 0
        else:
            self.state_bracket_rates = STATE_BRACKET_RATES[residence_state][married]
            self.state_standard_deduction = STATE_STD_DEDUCTION[residence_state][
                married
            ]
        self.federal_bracket_rates = FED_BRACKET_RATES[married]
        self.federal_standard_deduction = FED_STD_DEDUCTION[married]


def _bracket_math(brackets: list, yearly_income: float) -> float:
    """Calculates and returns taxes owed

    Args:
        brackets (list): List of brackets in format: [  rate,
                                                        highest dollar that rate applies to,
                                                        sum of tax owed in previous brackets]
        yearly_income (float): income in yearly amount

    Returns:
        (float): tax owed
    """
    if yearly_income == 0:
        return 0  # avoid bracket math if no income
    rate_idx, cap_idx, sum_idx = 0, 1, 2
    prev_bracket_cap = 0
    for bracket in brackets:
        if yearly_income < bracket[cap_idx]:
            # return tax owed up to prev bracket + tax owed in this bracket
            return -bracket[sum_idx] - bracket[rate_idx] * (
                yearly_income - prev_bracket_cap
            )
        prev_bracket_cap = bracket[cap_idx]
    raise ValueError("Income exceeds highest bracket")


def _social_security_tax(controller: JobIncomeController, state: State) -> float:
    """Computes the Social Security tax for a given income and date.

    The Social Security tax is calculated as a percentage of the eligible income,
    which is the minimum between the income and the maximum earnings extrapolated
    for the given date. The tax rate is defined by the constant SOCIAL_SECURITY_TAX_RATE.

    Calculates for both user and partner, if applicable.

    Args:
        controller (JobIncomeController): Controller for job income
        state (State): current state

    Returns:
        float: Social Security tax for the given income and date
    """
    max_earnings = max_earnings_extrapolator(state.date)
    user_eligible_income = min(
        max_earnings, controller.get_user_income(state.interval_idx)
    )
    partner_eligible_income = min(
        max_earnings, controller.get_partner_income(state.interval_idx)
    )
    return -SOCIAL_SECURITY_TAX_RATE * (user_eligible_income + partner_eligible_income)
