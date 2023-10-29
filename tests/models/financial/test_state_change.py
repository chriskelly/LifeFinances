"""Testing for models/financial/state_change.py
"""
# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name

import pytest
from app.data.constants import INTERVALS_PER_YEAR
from app.models.config import Kids, Spending
from app.models.controllers import Controllers
from app.models.financial.state import State
from app.models.financial.state_change import Income, StateChangeComponents


@pytest.fixture
def controllers_mock(mocker):
    """Fixture for an empty Controllers"""
    return mocker.MagicMock(spec=Controllers)


@pytest.fixture
def components_mock(mocker):
    """Fixture for an empty StateChangeComponents"""
    return mocker.MagicMock(spec=StateChangeComponents)


def test_income(
    controllers_mock: Controllers, first_state, components_mock: StateChangeComponents
):
    """Test that income is summed up correctly"""
    fake_values = [1, 2, 3, 4]
    controllers_mock.job_income.get_total_income = lambda *_: fake_values[0]
    controllers_mock.social_security.calc_payment = lambda *_: (
        fake_values[1],
        fake_values[2],
    )
    controllers_mock.pension.calc_payment = lambda *_: fake_values[3]
    components_mock.controllers = controllers_mock
    components_mock.state = first_state
    income = Income(components_mock)
    assert float(income) == pytest.approx(sum(fake_values))


class TestCalcSpending:
    yearly_amount = 50
    retirement_change = -0.1
    inflation = 2

    @pytest.fixture()
    def components_mock(
        self,
        first_state: State,
        components_mock: StateChangeComponents,
        controllers_mock: Controllers,
    ):
        """Initialize the mock components"""
        components_mock.state = first_state
        components_mock.state.user.spending = Spending(
            yearly_amount=self.yearly_amount, retirement_change=self.retirement_change
        )
        components_mock.state.inflation = self.inflation
        components_mock.controllers = controllers_mock
        return components_mock

    def test_while_working(self, components_mock: StateChangeComponents):
        """Spending should be unadjusted while working"""
        components_mock.controllers.job_income.is_working = lambda *_: True
        assert StateChangeComponents._calc_spending(components_mock) == pytest.approx(
            -self.yearly_amount / INTERVALS_PER_YEAR * self.inflation
        )

    def test_after_working(self, components_mock: StateChangeComponents):
        """Spending should be adjusted by the retirement change after working"""
        components_mock.controllers.job_income.is_working = lambda *_: False
        assert StateChangeComponents._calc_spending(components_mock) == pytest.approx(
            -self.yearly_amount
            / INTERVALS_PER_YEAR
            * self.inflation
            * (1 + self.retirement_change)
        )


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

    def calc_cost_from_birth_years(self, birth_years: list[float]):
        """Helper function to calculate the cost of kids"""
        self.components_mock.state.user.kids = Kids(
            fraction_of_spending=self.cost_of_each_kid / self.spending,
            birth_years=birth_years,
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
