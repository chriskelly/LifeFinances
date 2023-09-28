"""Testing for models/controllers/annuity.py"""
# pylint:disable=missing-class-docstring, redefined-outer-name, protected-access

import pytest
from app.data.constants import ANNUITY_INT_YIELD
from app.models.controllers.annuity import Controller
from app.models.financial.state import State
from app.models.controllers.job_income import Controller as JobIncomeController
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


class TestContributeToAnnuity:
    def test_contribute_to_annuity(self, controller: Controller, first_state: State):
        """Should contribute to annuity if balance is smaller than target annuity balance"""
        controller._balance = 0.5 * first_state.net_worth
        target_annuity_allocation = 0.6
        expected_contribution = (
            target_annuity_allocation * first_state.net_worth - controller._balance
        )
        contribution = controller._contribute_to_annuity(
            annuity_allocation=target_annuity_allocation, state=first_state
        )
        assert contribution == pytest.approx(expected_contribution)

    def test_target_balance_too_small(self, controller: Controller, first_state: State):
        """Should contribute 0 if target annuity balance is smaller than current balance"""
        controller._balance = 0.5 * first_state.net_worth
        target_annuity_allocation = 0.4
        contribution = controller._contribute_to_annuity(
            annuity_allocation=target_annuity_allocation, state=first_state
        )
        assert contribution == 0

    def test_balance_grows_too_large(self, controller: Controller, first_state: State):
        """Should contribute 0 if balance has grown larger than target
        annuity balance due to interest"""
        controller._balance = 0.5 * first_state.net_worth
        target_annuity_allocation = 0.6
        first_state.interval_idx = (
            10000  # Large interval idx to ensure balance grows above target
        )
        contribution = controller._contribute_to_annuity(
            annuity_allocation=target_annuity_allocation, state=first_state
        )
        assert contribution == 0


def test_annuitize(controller: Controller):
    """Should update the balance and annuitized flag while setting interest yield to 1"""
    initial_balance = 100
    controller._balance = initial_balance
    controller._annuitize(10)
    assert controller.annuitized
    assert controller._interest_yield == 1
    assert controller._balance > initial_balance


@pytest.fixture
def job_income_controller(sample_user: User):
    """Sample JobIncomeController based on `sample_configs/full_config.yml`"""
    return JobIncomeController(sample_user)


class TestCheckForAnnuityPayment:
    def test_net_worth_above_target(
        self,
        controller: Controller,
        first_state: State,
        job_income_controller: JobIncomeController,
    ):
        """Should return 0 when the net worth is above the
        inflation-adjusted target"""
        first_state.inflation = 2
        first_state.net_worth = (
            2 * first_state.user.portfolio.low_risk.annuities.net_worth_target + 1
        )
        payout = controller._check_for_annuity_payment(
            job_income_controller, first_state
        )
        assert payout == 0

    def test_user_still_working(
        self,
        controller: Controller,
        first_state: State,
        job_income_controller: JobIncomeController,
    ):
        """Annuity payout should be 0 when the user is still earning income"""
        job_income_controller._user_income[first_state.interval_idx] = 100
        payout = controller._check_for_annuity_payment(
            job_income_controller, first_state
        )
        assert payout == 0

    def test_annuitizes_properly(
        self,
        controller: Controller,
        first_state: State,
        job_income_controller: JobIncomeController,
    ):
        """Annuity shoulld annuitize when the net worth is below the target
        and the user is not working"""
        first_state.net_worth = (
            first_state.user.portfolio.low_risk.annuities.net_worth_target - 1
        )
        job_income_controller._user_income[first_state.interval_idx] = 0
        job_income_controller._partner_income[first_state.interval_idx] = 0
        controller.annuitized = False
        controller._check_for_annuity_payment(job_income_controller, first_state)
        assert controller.annuitized

        # Test that the annuity payout is correct when the annuity is annuitized
        controller._balance = 100
        payout = controller._check_for_annuity_payment(
            job_income_controller, first_state
        )
        assert payout == pytest.approx(controller._balance * controller._payout_rate)
