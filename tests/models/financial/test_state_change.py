"""Testing for models/financial/state_change.py
"""
# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name

import pytest
from app.data.constants import INTERVALS_PER_YEAR
from app.models.config import Kids, Spending
from app.models.financial.state import State
from app.models.financial.state_change import Income, _calc_cost_of_kids, _calc_spending


def test_income(mocker, first_state):
    """Test that income is summed up correctly"""
    fake_values = [1, 2, 3, 4]
    controllers_mock = mocker.MagicMock()
    controllers_mock.job_income.get_total_income = lambda *arg: fake_values[0]
    controllers_mock.social_security.calc_payment = lambda *arg: (
        fake_values[1],
        fake_values[2],
    )
    controllers_mock.pension.calc_payment = lambda *arg: fake_values[3]
    income = Income(state=first_state, controllers=controllers_mock)
    assert float(income) == pytest.approx(sum(fake_values))


class TestCalcSpending:
    yearly_amount = 50
    retirement_change = -0.1
    inflation = 2
    config = None
    state = None

    @pytest.fixture(autouse=True)
    def init(self, first_state: State):
        """Initialize the config and state"""
        self.config = Spending(
            yearly_amount=self.yearly_amount, retirement_change=self.retirement_change
        )
        self.state = first_state
        self.state.inflation = self.inflation

    def test_while_working(self, first_state: State):
        """Spending should be unadjusted while working"""
        is_working = True
        assert _calc_spending(
            state=first_state, config=self.config, is_working=is_working
        ) == pytest.approx(-self.yearly_amount / INTERVALS_PER_YEAR * self.inflation)

    def test_after_working(self, first_state: State):
        """Spending should be adjusted by the retirement change after working"""
        is_working = False
        assert _calc_spending(
            state=first_state, config=self.config, is_working=is_working
        ) == pytest.approx(
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
    birth_years = None
    config = None

    def calc_cost(self):
        """Helper function to calculate the cost of kids"""
        config = Kids(
            fraction_of_spending=self.cost_of_each_kid / self.spending,
            birth_years=self.birth_years,
            years_of_support=self.years_of_support,
        )
        return _calc_cost_of_kids(
            current_date=self.current_date,
            spending=self.spending,
            config=config,
        )

    def test_one_kid(self):
        """Test that the cost of one kid is calculated correctly"""
        self.birth_years = [2018]
        cost_of_kid = self.calc_cost()
        assert cost_of_kid == pytest.approx(self.cost_of_each_kid)

    def test_multiple_kids(self):
        """Test that the cost of multiple kids is calculated correctly"""
        self.birth_years = [2018, 2019]
        cost_of_kids = self.calc_cost()
        assert cost_of_kids == pytest.approx(
            len(self.birth_years) * self.cost_of_each_kid
        )

    def test_kid_not_born_yet(self):
        """Test that the cost of a kid not born yet is zero"""
        self.birth_years = [self.current_date + 1]
        cost_of_kids = self.calc_cost()
        assert cost_of_kids == pytest.approx(0)

    def test_kid_too_old(self):
        """Test that the cost of a kid that is older than `years_of_support` is zero"""
        self.birth_years = [self.current_date - (self.years_of_support + 1)]
        cost_of_kids = self.calc_cost()
        assert cost_of_kids == pytest.approx(0)
