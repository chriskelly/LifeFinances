"""Testing for models/financial/state_change.py
"""

# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name
# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

from typing import Sequence
import pytest
import numpy as np
from app.data.constants import INTERVALS_PER_YEAR
from app.models.config import Kids, Spending, SpendingProfile
from app.models.controllers import Controllers
from app.models.financial.state import State
from app.models.financial.state_change import Income, StateChangeComponents


def test_income(
    controllers_mock: Controllers, first_state, components_mock: StateChangeComponents
):
    """Test that income is summed up correctly"""
    fake_values = [1, 2, 3, 4]
    controllers_mock.job_income.get_total_income = lambda *_, **__: fake_values[0]
    controllers_mock.social_security.calc_payment = lambda *_, **__: (
        fake_values[1],
        fake_values[2],
    )
    controllers_mock.pension.calc_payment = lambda *_, **__: fake_values[3]
    components_mock.controllers = controllers_mock
    components_mock.state = first_state
    income = Income(components_mock)
    assert income.sum == pytest.approx(sum(fake_values))


def test_portfolio_return(
    mocker,
    components_mock: StateChangeComponents,
):
    """Test that portfolio return is calculated correctly"""
    net_worth = 100
    asset_rates = [0.2, -0.2]
    allocation = np.array([0.4, 0.6])
    dot_product = -0.04
    expected_return = net_worth * dot_product

    components_mock.state = mocker.MagicMock()
    components_mock.state.net_worth = net_worth
    components_mock.economic_data = mocker.MagicMock()
    components_mock.economic_data.asset_rates = asset_rates
    components_mock.allocation = allocation
    components_mock.controllers = mocker.MagicMock()

    portfolio_return = StateChangeComponents._calc_portfolio_return(components_mock)
    assert portfolio_return == pytest.approx(expected_return)


class TestCalcSpending:
    inflation = 2
    yearly_amounts = [5000, 6000, 7000]
    dates = [2021, 2022, 2023]

    @pytest.fixture()
    def components_mock(
        self,
        first_state: State,
        components_mock: StateChangeComponents,
    ):
        """Initialize the mock components"""
        components_mock.state = first_state
        components_mock.state.date = self.dates[0]
        components_mock.state.user.spending = Spending(
            profiles=[SpendingProfile(yearly_amount=self.yearly_amounts[0])]
        )
        components_mock.state.inflation = self.inflation
        return components_mock

    def test_single_profile(self, components_mock: StateChangeComponents):
        """Test that the spending is calculated correctly for a single profile"""
        spending = StateChangeComponents._calc_spending(components_mock)
        assert spending == pytest.approx(
            -self.yearly_amounts[0] / INTERVALS_PER_YEAR * self.inflation
        )

    def test_multiple_profiles(self, components_mock: StateChangeComponents):
        """Test that the spending is calculated correctly for multiple profiles"""
        components_mock.state.user.spending.profiles = [
            SpendingProfile(yearly_amount=yearly_amount, end_date=date)
            for yearly_amount, date in zip(self.yearly_amounts, self.dates)
        ]
        for i, date in enumerate(self.dates):
            components_mock.state.date = date
            spending = StateChangeComponents._calc_spending(components_mock)
            assert spending == pytest.approx(
                -self.yearly_amounts[i] / INTERVALS_PER_YEAR * self.inflation
            )

    def test_no_matching_profile(self, components_mock: StateChangeComponents):
        """Test that an error is raised if the last profile has a date (which it shouldn't)
        before the current date"""
        date = 2020
        components_mock.state.user.spending.profiles = [
            SpendingProfile(yearly_amount=1000, end_date=date)
        ]
        components_mock.state.date = date + 1
        with pytest.raises(ValueError):
            StateChangeComponents._calc_spending(components_mock)


class TestCalcCostOfKids:
    spending = -100
    cost_of_each_kid = -20
    current_date = 2020
    years_of_support = 18
    components_mock: StateChangeComponents

    @pytest.fixture(autouse=True)
    def init_components_mock(
        self, first_state: State, components_mock: StateChangeComponents
    ):
        """Initialize the mock components"""
        self.components_mock = components_mock
        self.components_mock.state = first_state
        self.components_mock.state.date = self.current_date

    def calc_cost_from_birth_years(self, birth_years: Sequence[float]):
        """Helper function to calculate the cost of kids"""
        self.components_mock.state.user.kids = Kids(
            fraction_of_spending=self.cost_of_each_kid / self.spending,
            birth_years=list(birth_years),
            years_of_support=self.years_of_support,
        )
        return StateChangeComponents._calc_cost_of_kids(
            components=self.components_mock,
            spending=self.spending,
        )

    def test_one_kid(self):
        """Test that the cost of one kid is calculated correctly"""
        cost_of_kid = self.calc_cost_from_birth_years([2018])
        assert cost_of_kid == pytest.approx(self.cost_of_each_kid)

    def test_multiple_kids(self):
        """Test that the cost of multiple kids is calculated correctly"""
        birth_years = [2018, 2019]
        cost_of_kids = self.calc_cost_from_birth_years(birth_years)
        assert cost_of_kids == pytest.approx(len(birth_years) * self.cost_of_each_kid)

    def test_kid_not_born_yet(self):
        """Test that the cost of a kid not born yet is zero"""
        cost_of_kids = self.calc_cost_from_birth_years([self.current_date + 1])
        assert cost_of_kids == pytest.approx(0)

    def test_kid_too_old(self):
        """Test that the cost of a kid that is older than `years_of_support` is zero"""
        birth_years = [self.current_date - (self.years_of_support + 1)]
        cost_of_kids = self.calc_cost_from_birth_years(birth_years)
        assert cost_of_kids == pytest.approx(0)
