"""Model of a financial annuity"""

from app import util
from app.data.constants import (
    ANNUITY_INT_YIELD,
    ANNUITY_PAYOUT_RATE,
    INTERVALS_PER_YEAR,
)
from app.models.config import User
from app.models.financial.state import State
from app.models.controllers.job_income import Controller as JobIncomeController
from app.util import interval_yield


class Controller:
    """Controller for a fixed annuity

    Methods:
        make_annuity_transaction() -> float:
            If applicable, contribute to annuity and/or take payment from annuity
    """

    def __init__(self, user: User):
        if (
            user.portfolio.annuity is None
            or user.portfolio.annuity.contribution_rate == 0
        ):
            self._no_annuity = True
            return
        self._no_annuity = False
        self._interest_yield = interval_yield(ANNUITY_INT_YIELD)
        self._payout_rate = ANNUITY_PAYOUT_RATE / INTERVALS_PER_YEAR
        self._prev_transaction_interval_idx = 0
        self._balance = 0
        self._contribution_rate = user.portfolio.annuity.contribution_rate
        self._annuitized = False
        self._net_worth_target = (
            user.portfolio.annuity.net_worth_target if user.portfolio.annuity else 0
        )

    def make_annuity_transaction(
        self,
        state: State,
        job_income_controller: JobIncomeController,
        initial_net_transaction: float,
    ) -> float:
        """If applicable, contribute to annuity and/or take payment from annuity


        Args:
            state (State): current state

            job_income_controller (JobIncomeController): used to confirm if
            user/partner are still working

            initial_net_transaction (float): net income (minus costs)

        Returns:
            float: The net transaction of annuity payment minus contribution
        """
        if self._no_annuity:
            return 0
        contribution = util.constrain(
            value=self._contribution_rate * initial_net_transaction, low=0
        )
        self._balance += contribution
        payment = self._check_for_annuity_payment(
            job_income_controller=job_income_controller, state=state
        )
        net_transaction = payment - contribution
        return net_transaction

    def _apply_interest_to_balance(self, interval_idx: int) -> float:
        """Update and return balance for interest gained. Interest yield will be 1 when annuitized.

        Args:
            interval_idx (int): state interval index

        Returns:
            float: Balance as of input date index
        """
        self._balance *= self._interest_yield ** (
            interval_idx - self._prev_transaction_interval_idx
        )
        self._prev_transaction_interval_idx = interval_idx
        return self._balance

    def _check_for_annuity_payment(
        self, job_income_controller: JobIncomeController, state: State
    ) -> float:
        working = job_income_controller.get_total_income(state.interval_idx) > 0
        # Trigger the annuity when net worth is below target. To ensure that
        # it's not triggered too early, wait until at least user isn't working
        # anymore. Also, don't trigger if annuity is already annuitized.
        if (
            state.net_worth < self._net_worth_target * state.inflation
            and not working
            and not self._annuitized
        ):
            self._annuitize(state.interval_idx)
        if self._annuitized:
            # Not tied to inflation since it's a fixed annuity.
            # Inflation based annuities are more complex and less available.
            return self._balance * self._payout_rate
        return 0

    def _annuitize(self, interval_idx: int):
        """Annuitize this annuity

        Args:
            interval_idx (int): state interval index

        Yields:
            no return: Balance is updated for interest gained. No interest gained after this point
        """
        self._apply_interest_to_balance(interval_idx)  # add interest for last time
        self._annuitized = True
        self._interest_yield = 1
        # After annuitization, balance does not grow anymore except for contributions.
