"""Testing for models/financial/state_change.py
"""
# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name

import pytest
from app.models.config import Spending
from app.models.financial.state import State
from app.models.financial.state_change import _calc_spending


class TestCalcSpending:
    yearly_amount = 50
    retirement_change = -0.1
    inflation = 2
    config = None
    state = None

    @pytest.fixture(autouse=True)
    def init(self, first_state: State):
        self.config = Spending(
            yearly_amount=self.yearly_amount, retirement_change=self.retirement_change
        )
        self.state = first_state
        self.state.inflation = self.inflation

    def test_while_working(self, first_state: State):
        is_working = True
        assert _calc_spending(
            state=first_state, config=self.config, is_working=is_working
        ) == pytest.approx(-self.yearly_amount * self.inflation)

    def test_after_working(self, first_state: State):
        is_working = False
        assert _calc_spending(
            state=first_state, config=self.config, is_working=is_working
        ) == pytest.approx(
            -self.yearly_amount * self.inflation * (1 + self.retirement_change)
        )
