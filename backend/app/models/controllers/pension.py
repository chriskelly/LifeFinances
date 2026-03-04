"""Model of Admin's Pension

For now, this model is not intended for general use and applies
the specific rules of the admin's pension.
"""

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import cast

from app.data import constants
from app.data.constants import INTERVALS_PER_YEAR
from app.models.config import IncomeProfile, NetWorthStrategyConfig, User
from app.models.financial.state import State
from app.util import interval_yield

BENEFIT_RATES = {
    2043: 0.0116,
    2044: 0.0128,
    2045: 0.0140,
    2046: 0.0152,
    2047: 0.0164,
    2048: 0.0176,
    2049: 0.0188,
    2050: 0.0200,
    2051: 0.0213,
    2052: 0.0227,
    2053: 0.0240,
}
"""Pension details for admin. Format: {year:rate}"""
PENSION_CONTRIBUTION = 0.09  # 9% of income
"""Last date of update"""
INTEREST_YIELD = 1.02  # varies from 1.2-3% based on Progress Reports
EARLY_YEAR = 2043
MID_YEAR = 2048
LATE_YEAR = 2053
JOB_START_DATE = 2016
JOB_BREAKS: list[tuple[float, float]] = []
"""Any unpaid breaks in format [(start date, end date), ...]"""
FINAL_COMPENSATION = 109.5


class _Strategy(ABC):
    """Abstract allocation strategy class.

    Required methods:
        calc_payment(self, state: State) -> float:
    """

    @abstractmethod
    def calc_payment(self, state: State) -> float:
        """Calculate pension payment based on current state

        Args:
            state (State): current state

        Returns:
            float: pension payment for interval
        """


class _AgeStrategy(_Strategy):
    def __init__(self, trigger_year: int, base: float):
        self._trigger_date = trigger_year
        benefit_rate = BENEFIT_RATES[trigger_year]
        self._payment = base * benefit_rate

    def calc_payment(self, state: State) -> float:
        if state.date >= self._trigger_date:
            return self._payment * state.inflation
        return 0


class _NetWorthStrategy(_Strategy):
    def __init__(self, config: NetWorthStrategyConfig, base: float):
        if config.net_worth_target is None:
            raise ValueError("Net worth target cannot be None")
        self._net_worth_target = config.net_worth_target
        self._base = base
        self._payment = None
        self._benefit_rate = None

    def calc_payment(self, state: State) -> float:
        if self._payment:
            return self._payment * state.inflation
        if (
            state.date >= EARLY_YEAR
            and state.net_worth < self._net_worth_target * state.inflation
        ) or state.date == LATE_YEAR:
            self._benefit_rate = BENEFIT_RATES[math.trunc(state.date)]
            self._payment = self._base * self._benefit_rate
            return self._payment * state.inflation
        return 0


class _CashOutStrategy(_Strategy):
    """
    Args:
        user (User)
    """

    def __init__(self, user: User):
        if user.admin is None:
            raise ValueError("Admin cannot be None")
        if user.partner is None:
            raise ValueError("Partner cannot be None")
        if user.partner.income_profiles is None:
            raise ValueError("Income profiles cannot be None")
        self._pension = user.admin.pension
        self._income_profile = user.partner.income_profiles[0]
        self._interval_raise = interval_yield(1 + self._income_profile.yearly_raise)
        self._est_prev_interval_income = self._calc_est_prev_interval_income()
        self._cash_out_date = self._income_profile.last_date
        self._pension_balance = self._calc_pension_balance()

    def _calc_est_prev_interval_income(self) -> float:
        """Estimate the interval income at the time when account balance was last updated"""
        age_of_data = self._intervals_between(
            self._pension.balance_update, constants.TODAY_YR_QT
        )
        # Estimate interval income at the time of last update
        interval_income = self._income_profile.starting_income / INTERVALS_PER_YEAR
        return interval_income / (self._interval_raise**age_of_data)

    def _calc_pension_balance(self) -> float:
        """Estimate pension balance at cash out date"""
        working_intervals = self._intervals_between(
            self._cash_out_date, self._pension.balance_update
        )
        pension_balance = self._pension.account_balance
        income = self._est_prev_interval_income
        interval_interest = interval_yield(INTEREST_YIELD)
        for _ in range(working_intervals):
            pension_balance *= interval_interest
            pension_balance += income * PENSION_CONTRIBUTION
            income *= self._interval_raise
        return pension_balance

    def _intervals_between(self, one_date: float, another_date: float) -> int:
        """Calculate the qty of intervals between dates. Input order doesn't matter"""
        if another_date >= one_date:
            return round((another_date - one_date) * INTERVALS_PER_YEAR)
        return self._intervals_between(another_date, one_date)

    def calc_payment(self, state: State) -> float:
        if math.isclose(state.date, self._cash_out_date):
            return self._pension_balance
        return 0


class Controller:
    """Manages pension strategy and payment generation.

    The Defined Benefit Program provides a monthly benefit based on a formula:
    `service credit x age factor x final compensation = your retirement benefit`

    Methods:
        calc_payment(self, state: State) -> float: Calculate pension payment for interval

    """

    def __init__(self, user: User):
        self._user = user
        if user.admin and user.partner:
            self._pension = user.admin.pension
            base = Controller._calc_base(user.partner.income_profiles)
            self._strategy = self._gen_strategy(base)
        else:
            self._strategy = None

    @staticmethod
    def _calc_base(income_profiles: list[IncomeProfile] | None) -> float:
        """Calculate the interval value to multiply against the benefit rates

        This is the `service credit x final compensation` portion of the pension formula
        """
        prev_years_on_break = Controller._calc_years_on_break(JOB_BREAKS)
        prev_years_worked = constants.TODAY_YR_QT - JOB_START_DATE - prev_years_on_break
        years_worked = prev_years_worked + Controller._years_left_to_work(
            income_profiles=income_profiles, current_date=constants.TODAY_YR_QT
        )
        final_compensation = (
            FINAL_COMPENSATION
            if not income_profiles
            else income_profiles[-1].starting_income
        )
        return final_compensation * years_worked / INTERVALS_PER_YEAR

    @staticmethod
    def _calc_years_on_break(job_breaks: Sequence[tuple[float, float]]) -> float:
        """Calculate the years on break"""
        return sum(end - start for start, end in job_breaks)

    @staticmethod
    def _years_left_to_work(
        income_profiles: list[IncomeProfile] | None, current_date: float
    ) -> float:
        years_worked = 0
        if income_profiles is not None:
            date = current_date
            for profile in income_profiles:
                if profile.starting_income != 0:
                    years_worked += profile.last_date - date
                date = profile.last_date
        return years_worked

    def _gen_strategy(self, base: float) -> _Strategy:
        (
            strategy_str,
            strategy_obj,
        ) = self._pension.strategy.chosen_strategy
        match strategy_str:
            case "early":
                return _AgeStrategy(trigger_year=EARLY_YEAR, base=base)
            case "mid":
                return _AgeStrategy(trigger_year=MID_YEAR, base=base)
            case "late":
                return _AgeStrategy(trigger_year=LATE_YEAR, base=base)
            case "net_worth":
                return _NetWorthStrategy(
                    config=cast(NetWorthStrategyConfig, strategy_obj), base=base
                )
            case "cash_out":
                return _CashOutStrategy(self._user)
            case _:
                raise ValueError(
                    f"Invalid strategy: {self._pension.strategy.chosen_strategy}"
                )

    def calc_payment(self, state: State) -> float:
        """Calculate pension payment for interval adjusted by trust factor

        Args:
            state (State): current state

        Returns:
            float: Interval payment

        Raises:
            ValueError: If state.user.admin is None
        """
        if not self._strategy:
            return 0
        if state.user.admin is None:
            raise ValueError(
                "state.user.admin cannot be None when calculating pension payment"
            )
        payment = self._strategy.calc_payment(state)
        return payment * state.user.admin.pension.trust_factor
