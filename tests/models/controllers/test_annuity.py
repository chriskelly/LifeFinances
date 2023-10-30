"""Testing for models/controllers/annuity.py"""
# pylint:disable=missing-class-docstring, redefined-outer-name, protected-access

import pytest
from app.data.constants import ANNUITY_INT_YIELD
from app.models.controllers.annuity import Controller
from app.models.financial.state import State
from app.models.config import User
from app.util import interval_yield


@pytest.fixture
def controller(sample_user: User):
    """Sample Annuity Controller based on `sample_configs/full_config.yml`"""
    return Controller(sample_user)


def test_apply_interest_to_balance(controller: Controller):
    """Should update and return balance based on
    interest yield and interval idx"""
    interest_yield = interval_yield(ANNUITY_INT_YIELD)
    initial_balance = 100
    initial_interval_idx = 2
    final_interval_idx = 10
    intervals_inbetween = final_interval_idx - initial_interval_idx

    controller._balance = initial_balance
    controller._prev_transaction_interval_idx = initial_interval_idx
    expected_balance = initial_balance * interest_yield**intervals_inbetween
    returned_balance = controller._apply_interest_to_balance(10)
    assert returned_balance == pytest.approx(expected_balance)
    assert controller._balance == pytest.approx(expected_balance)


def test_annuitize(controller: Controller):
    """Should update the balance and annuitized flag while setting interest yield to 1"""
    initial_balance = 100
    controller._balance = initial_balance
    controller._annuitize(10)
    assert controller._annuitized
    assert controller._interest_yield == 1
    assert controller._balance > initial_balance


class TestCheckForAnnuityPayment:
    def test_net_worth_above_target(
        self,
        controller: Controller,
        first_state: State,
    ):
        """Should return 0 when the net worth is above the
        inflation-adjusted target"""
        first_state.inflation = 2
        first_state.net_worth = (
            2 * first_state.user.portfolio.annuity.net_worth_target + 1
        )
        payout = controller._check_for_annuity_payment(
            is_working=False, state=first_state
        )
        assert payout == 0

    def test_user_still_working(
        self,
        controller: Controller,
        first_state: State,
    ):
        """Annuity payout should be 0 when the user is still earning income"""
        payout = controller._check_for_annuity_payment(
            is_working=True, state=first_state
        )
        assert payout == 0

    def test_annuitizes_properly(
        self,
        controller: Controller,
        first_state: State,
    ):
        """Annuity shoulld annuitize when the net worth is below the target
        and the user is not working"""
        first_state.net_worth = first_state.user.portfolio.annuity.net_worth_target - 1
        controller._annuitized = False
        controller._check_for_annuity_payment(is_working=False, state=first_state)
        assert controller._annuitized

        # Test that the annuity payout is correct when the annuity is annuitized
        controller._balance = 100
        payout = controller._check_for_annuity_payment(
            is_working=False, state=first_state
        )
        assert payout == pytest.approx(controller._balance * controller._payout_rate)
