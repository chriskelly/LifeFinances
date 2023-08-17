"""Job Income Stream Module

Classes:
    Controller: Generate and provide timelines of job income
"""

from dataclasses import dataclass
from app.data import constants
from app.models.config import IncomeProfile, User


@dataclass
class _Income:
    """Dataclass to represent an interval of an `IncomeProfile`

    Attributes:
        amount (float): Income amount for the interval

        tax_deferred (float): Amount of income that is tax deferred

        try_to_optimize (bool): Whether to try to optimize the income

        social_security_eligible (bool): Whether the income is eligible for social security
    """

    amount: float = 0
    tax_deferred: float = 0
    try_to_optimize: bool = False
    social_security_eligible: bool = False


class Controller:
    """Class of income timelines

    Attributes:
        user_timeline (list[Income]): Timeline of user income

        partner_timeline (list[Income]): Timeline of partner income

    Methods:
        get_user_income(interval_idx): Get the user income for a given interval

        get_partner_income(interval_idx): Get the partner income for a given interval

        get_total_income(interval_idx): Get the total income for a given interval

        get_taxable_income(interval_idx): Get the taxable income for a given interval

    """

    def __init__(self, user_config: User):
        self._size = user_config.intervals_per_trial
        self.user_timeline = self._gen_timeline(user_config.income_profiles)
        self.partner_timeline = self._gen_timeline(user_config.partner.income_profiles)
        self._user_income = [income.amount for income in self.user_timeline]
        self._partner_income = [income.amount for income in self.partner_timeline]
        self._tax_deferred = [
            user_income.tax_deferred + partner_income.tax_deferred
            for user_income, partner_income in zip(
                self.user_timeline, self.partner_timeline
            )
        ]

    def _gen_timeline(self, profiles: list[IncomeProfile]) -> list[_Income]:
        """Generate a list of Income objects

        Args:
            profiles (list[IncomeProfile])

        Returns:
            list[Income] An Income object for each trial interval (including empty ones)
        """

        def _get_income_and_deferral_ratio(profile: IncomeProfile):
            """Provide starting income and the ratio between deferred income and starting income"""
            income = profile.starting_income
            try:
                deferral_ratio = profile.tax_deferred_income / income
            except ZeroDivisionError:
                deferral_ratio = 0
            return income, deferral_ratio

        if not profiles:
            return [_Income() for _ in range(self._size)]
        date = constants.TODAY_YR_QT
        timeline = []
        idx = 0
        income, deferral_ratio = _get_income_and_deferral_ratio(profiles[idx])
        while True:
            timeline.append(
                _Income(
                    amount=income,
                    tax_deferred=deferral_ratio * income,
                    try_to_optimize=profiles[idx].try_to_optimize,
                    social_security_eligible=profiles[idx].social_security_eligible,
                )
            )
            date += 0.25
            if date > profiles[idx].last_date:  # end of profile
                idx += 1
                if idx >= len(profiles):  # no more profiles
                    break
                income, deferral_ratio = _get_income_and_deferral_ratio(profiles[idx])
            elif date % 1 == 0:  # new year
                income *= 1 + profiles[idx].yearly_raise
        remaining_timeline = [_Income() for _ in range(self._size - len(timeline))]
        return timeline + remaining_timeline

    def get_user_income(self, interval_idx: int) -> float:
        """Get the user income for a given interval

        Args:
            interval_idx (int): Index of interval

        Returns:
            float
        """
        return self._user_income[interval_idx]

    def get_partner_income(self, interval_idx: int) -> float:
        """Get the partner income for a given interval

        Args:
            interval_idx (int): Index of interval

        Returns:
            float
        """
        return self._partner_income[interval_idx]

    def get_total_income(self, interval_idx: int) -> float:
        """Get the total income for a given interval

        Args:
            interval_idx (int): Index of interval

        Returns:
            float
        """
        return self.get_user_income(interval_idx) + self.get_partner_income(
            interval_idx
        )

    def get_taxable_income(self, interval_idx: int) -> float:
        """Get the taxable income (from both user and partner) for a given interval

        Args:
            interval_idx (int): Index of interval

        Returns:
            float
        """
        return self.get_total_income(interval_idx) - self._tax_deferred[interval_idx]
