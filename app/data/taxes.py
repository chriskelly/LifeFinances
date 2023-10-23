"""Tax Rates and Functions

This module contains the constants related to taxes across all supported states.

"""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from app import util
from app.data.constants import INTERVALS_PER_YEAR

# pylint: disable=used-before-assignment
if TYPE_CHECKING:
    from app.models.financial.state_change import Income
    from app.models.financial.state import State


FED_STD_DEDUCTION = [12.950, 25.900]
"""2022 federal standard deduction"""
FED_BRACKET_RATES = [
    [
        [0.1, 10.275, 0],
        [0.12, 41.775, 1.027],
        [0.22, 89.075, 4.807],
        [0.24, 170.050, 15.213],
        [0.32, 215.950, 34.647],
        [0.35, 539.900, 49.335],
        [0.37, float("inf"), 162.718],
    ],
    [
        [0.1, 20.500, 0],
        [0.12, 83.550, 2.05],
        [0.22, 178.150, 9.616],
        [0.24, 340.100, 30.428],
        [0.32, 431.900, 69.296],
        [0.35, 647.850, 98.672],
        [0.37, float("inf"), 174.254],
    ],
]
"""2022 federal brackets for income tax in format
[rate,highest dollar that rate applies to,sum of tax owed in previous brackets]"""

# Code to calc third column of bracket rates
# from data import taxes
# brackets_set = taxes.STATE_BRACKET_RATES['New York']
# rate_idx, cap_idx = 0, 1
# for brackets in brackets_set:
#     res = [0,round(brackets[0][rate_idx] * brackets[0][cap_idx], 3)] # first 2
#     for i in range(1,len(brackets)-1):
#         res.append(round(res[-1] + brackets[i][rate_idx]*(brackets[i][cap_idx]
#                                                           -brackets[i-1][cap_idx]), 3))
#     for i in range(len(res)-1):
#         print(f'{[brackets[i][rate_idx], brackets[i][cap_idx], res[i]]},')
#     print(f"[{brackets[-1][rate_idx]}, float('inf'), {res[-1]}]")

STATE_STD_DEDUCTION = {
    "California": [4.803, 9.606],  # 2022
    "New York": [8.000, 16.050],  # 2022
}
"""State standard deduction. state:[single, married]"""
STATE_BRACKET_RATES = {
    "California": [  # 2022
        [
            [0.01, 9.325, 0],
            [0.02, 22.107, 0.093],
            [0.04, 34.892, 0.348],
            [0.06, 48.435, 0.860],
            [0.08, 61.214, 1.672],
            [0.093, 312.686, 2.695],
            [0.103, 375.221, 26.082],
            [0.113, 625.369, 32.523],
            [0.123, float("inf"), 60.789],
        ],
        [
            [0.01, 18.649, 0],
            [0.02, 44.213, 0.186],
            [0.04, 69.783, 0.698],
            [0.06, 96.869, 1.720],
            [0.08, 122.427, 3.346],
            [0.093, 625.371, 5.390],
            [0.103, 750.442, 52.164],
            [0.113, 1250.738, 65.046],
            [0.123, float("inf"), 121.580],
        ],
    ],
    "New York": [  # 2022
        [
            [0.04, 8.501, 0],
            [0.045, 11.701, 0.34],
            [0.0525, 13.901, 0.484],
            [0.0585, 80.651, 0.599],
            [0.0625, 215.401, 4.504],
            [0.0685, 1077.551, 12.926],
            [0.0965, 5000.001, 71.983],
            [0.103, 25000.001, 450.499],
            [0.109, float("inf"), 2510.499],
        ],
        [
            [0.04, 17.151, 0],
            [0.045, 23.601, 0.686],
            [0.0525, 27.901, 0.976],
            [0.0585, 161.551, 1.202],
            [0.0625, 323.201, 9.021],
            [0.0685, 2155.351, 19.124],
            [0.0965, 5000.001, 144.626],
            [0.103, 25000.001, 419.135],
            [0.109, float("inf"), 2479.135],
        ],
    ],
}
"""State brackets for income tax in format {state:[single brackets, married brackets]}.\n
Brackets in format [rate,highest dollar that rate applies to,
sum of tax owed in previous brackets]"""


@dataclass
class Taxes(util.FloatRepr):
    """Taxes paid in a given interval

    Attributes:
        income (float): income taxes on job income or social security
        medicare (float): medicare taxes as part of FICA
        social_security (float): social security taxes as part of FICA
        portfolio (float): taxes on portfolio income

    Returns:
        _type_: _description_
    """

    income: float
    medicare: float = -1
    social_security: float = -1
    portfolio: float = -1

    def __float__(self):
        return float(
            sum(
                [
                    self.income,
                    self.medicare,
                    self.social_security,
                    self.portfolio,
                ]
            )
        )


def calc_taxes(total_income: Income, taxable_income: float, state: State) -> Taxes:
    """Calculates taxes for a given interval

    Args:
        total_income (Income)
        taxable_income (float)
        state (State)

    Returns:
        Taxes: Attributes: income, medicare, social_security, portfolio
    """
    job_income_tax = _calc_income_taxes(interval_income=taxable_income, state=state)
    pension_income_tax = 0.8 * _calc_income_taxes(
        interval_income=total_income.social_security_user
        + total_income.social_security_partner
        + total_income.pension,
        state=state,
    )
    return Taxes(
        income=job_income_tax + pension_income_tax,
    )


def _calc_income_taxes(interval_income: float, state: State) -> float:
    """Combines federal and state taxes on non-tax-deferred income

    Args:
        interval_income (float): income in quarterly amount
        state (State): current state

    Returns:
        (float): federal and state tax burden for that quarter
    """
    if interval_income == 0.0:
        return 0  # avoid bracket math if no income

    inflation = state.inflation
    married = bool(state.user.partner)
    residence_state = state.user.state

    adj_income = (
        INTERVALS_PER_YEAR * interval_income / inflation
    )  # convert income to yearly and adjust for inflation
    fed_taxes = _bracket_math(
        brackets=FED_BRACKET_RATES[married],
        yearly_income=util.constrain(adj_income - FED_STD_DEDUCTION[married], low=0),
    )
    if residence_state is None:
        state_taxes = 0
    else:
        state_taxes = _bracket_math(
            brackets=STATE_BRACKET_RATES[residence_state][married],
            yearly_income=util.constrain(
                adj_income - STATE_STD_DEDUCTION[residence_state][married], low=0
            ),
        )
    return (fed_taxes + state_taxes) / INTERVALS_PER_YEAR


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
