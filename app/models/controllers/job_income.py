"""Job Income Stream Module

Classes:
    Controller: Generate and provide timelines of job income
"""

import numpy as np
from app.data import constants
from app.models.config import IncomeProfile, User


class Controller:
    """Class of income timelines

    Methods:
        get_user_income(interval_idx): Get the user income for a given interval

        get_partner_income(interval_idx): Get the partner income for a given interval

        get_total_income(interval_idx): Get the total income for a given interval

        get_taxable_income(interval_idx): Get the taxable income for a given interval

    """

    def __init__(self, user_config: User):
        self._size = user_config.intervals_per_trial
        self._tax_deferred = np.zeros(self._size)
        self._user = self._gen_timeline_and_update_tax_deferred(
            user_config.income_profiles
        )
        self._partner = self._gen_timeline_and_update_tax_deferred(
            user_config.partner.income_profiles
        )

    def _gen_timeline_and_update_tax_deferred(
        self,
        profiles: list[IncomeProfile],
    ) -> np.ndarray:
        """Generate a timeline of income and update the tax deferred income

        During income processing, the tax deferred timeline is updated to reflect
        the tax deferred income for each user/partner income profile.

        While doing both at the same time is not ideal, it can't be separated since
        the deferral ratio changes with each income profile.

        Args:
            profiles (list[IncomeProfile])

        Returns:
            np.ndarray: income timeline.

            Tax deferred income is updated in the class, not returned.
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
            return np.zeros(self._size)
        date = constants.TODAY_YR_QT
        timeline = []
        idx = 0
        income, deferral_ratio = _get_income_and_deferral_ratio(profiles[idx])
        while True:
            self._tax_deferred[len(timeline)] += deferral_ratio * income
            timeline.append(income)
            date += 0.25
            if date > profiles[idx].last_date:
                idx += 1
                if idx >= len(profiles):
                    break
                income, deferral_ratio = _get_income_and_deferral_ratio(profiles[idx])
            elif date % 1 == 0:  # new year
                income *= 1 + profiles[idx].yearly_raise
        remaining_timeline = np.zeros(self._size - len(timeline))
        return np.concatenate((timeline, remaining_timeline))

    def get_user_income(self, interval_idx: int) -> float:
        """Get the user income for a given interval

        Args:
            interval_idx (int): Index of interval

        Returns:
            float
        """
        return self._user[interval_idx]

    def get_partner_income(self, interval_idx: int) -> float:
        """Get the partner income for a given interval

        Args:
            interval_idx (int): Index of interval

        Returns:
            float
        """
        return self._partner[interval_idx]

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
