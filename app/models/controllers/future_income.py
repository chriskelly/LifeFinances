"""Module for computing future income and total portfolio value

Classes:
    Controller: Manages future income calculation and present value computation
"""

import numpy as np
import numpy_financial as npf

from app.data import constants
from app.models.config import User
from app.models.financial.state import State
from app.util import interval_yield


class _FakeState:
    """Lightweight stand-in for State used when precomputing future income.

    Accessing `net_worth` on this fake state is prohibited to ensure that
    benefit timing does not depend on future net worth during precomputation.
    """

    def __init__(self, *, user: User, date: float, interval_idx: int, inflation: float):
        self.user = user
        self.date = date
        self.interval_idx = interval_idx
        self.inflation = inflation

    @property  # pragma: no cover - defensive safety
    def net_worth(self) -> float:
        raise RuntimeError(
            "net_worth access is not allowed on fake states used for income precomputation"
        )


class Controller:
    """Manages future income calculation and total portfolio value computation.

    This controller precomputes future income streams (job + benefits) and provides
    methods to calculate present value of future income and total portfolio value.
    Computation is lazy by default and can be explicitly triggered or recalculated.

    Attributes:
        _user: User configuration
        _job_income_controller: Controller for job income
        _social_security_controller: Controller for social security benefits
        _pension_controller: Controller for pension benefits
        _economic_data_controller: Controller for economic data (inflation)
        _job_income_by_interval: Cached job income array per interval
        _benefit_income_by_interval: Cached benefit income array per interval
        _future_income_by_interval: Cached total future income array per interval
    """

    def __init__(
        self,
        user: User,
        job_income_controller,
        social_security_controller,
        pension_controller,
        economic_data_controller,
    ):
        """Initialize FutureIncomeController with dependencies.

        Args:
            user: User configuration
            job_income_controller: Controller for job income calculations
            social_security_controller: Controller for social security benefits
            pension_controller: Controller for pension benefits
            economic_data_controller: Controller for economic data (inflation)
        """
        self._user = user
        self._job_income_controller = job_income_controller
        self._social_security_controller = social_security_controller
        self._pension_controller = pension_controller
        self._economic_data_controller = economic_data_controller

        # Initialize cached arrays as None (lazy computation)
        self._job_income_by_interval: np.ndarray | None = None
        self._benefit_income_by_interval: np.ndarray | None = None
        self._future_income_by_interval: np.ndarray | None = None

    def compute_future_income(self, state: State) -> None:
        """Precompute job, benefit, and total future income per interval.

        This method forces computation (or recomputation) of income arrays.
        It uses a fake state to prevent benefit calculations from depending
        on future net worth values.

        Args:
            state: Current simulation state (used to access user config)
        """
        intervals_per_trial = self._user.intervals_per_trial

        # Initialize arrays
        job_income = np.zeros(intervals_per_trial, dtype=float)
        benefit_income = np.zeros(intervals_per_trial, dtype=float)

        for interval_idx in range(intervals_per_trial):
            # Calculate job income for this interval
            job_income[interval_idx] = self._job_income_controller.get_total_income(
                interval_idx
            )

            # Get actual cumulative inflation for this interval
            economic_data = self._economic_data_controller.get_economic_state_data(
                interval_idx
            )

            # Create fake state for benefits – forbid net_worth access
            fake_state = _FakeState(
                user=self._user,
                date=constants.TODAY_YR_QT
                + interval_idx * constants.YEARS_PER_INTERVAL,
                interval_idx=interval_idx,
                inflation=economic_data.inflation,
            )

            # Calculate benefit payments (controllers may return zero if not configured)
            # Type ignore: _FakeState is compatible with State for controller methods
            ss_user, ss_partner = self._social_security_controller.calc_payment(
                fake_state  # type: ignore[arg-type]
            )
            pension_payment = self._pension_controller.calc_payment(
                fake_state  # type: ignore[arg-type]
            )

            benefit_income[interval_idx] = ss_user + ss_partner + pension_payment

        # Store computed arrays
        self._job_income_by_interval = job_income
        self._benefit_income_by_interval = benefit_income
        self._future_income_by_interval = job_income + benefit_income

    def get_future_income_by_interval(self) -> np.ndarray | None:
        """Get precomputed future income array.

        Returns:
            Array of total income per interval, or None if not yet computed
        """
        return self._future_income_by_interval

    def get_future_income_pv(self, state: State, discount_rate_annual: float) -> float:
        """Calculate present value of future income.

        This method triggers lazy computation if arrays have not been computed yet.
        It calculates the NPV of all income from the next interval onward, using
        the specified discount rate.

        Args:
            state: Current simulation state
            discount_rate_annual: Annual discount rate for NPV calculation

        Returns:
            Present value of future income streams
        """
        # Lazily compute income arrays if not already done
        if self._future_income_by_interval is None:
            self.compute_future_income(state=state)

        # Convert annual discount rate to interval rate
        discount_rate_interval = interval_yield(1.0 + discount_rate_annual) - 1.0

        # Slice future income from the next interval onward
        assert self._future_income_by_interval is not None  # For type checkers
        start_idx = state.interval_idx + 1
        if start_idx >= len(self._future_income_by_interval):
            income_array = np.array([], dtype=float)
        else:
            income_array = self._future_income_by_interval[start_idx:]

        # Calculate NPV
        if income_array.size == 0:
            return 0.0

        # NOTE: numpy_financial.npv treats values[0] as occurring at time 0 (undiscounted).
        # Our income_array starts at the *next* interval (t=1), so prepend a 0 at t=0
        # to ensure the first future payment is discounted correctly.
        npv_values = np.concatenate(([0.0], income_array.astype(float)))
        future_income_pv = float(
            npf.npv(rate=discount_rate_interval, values=npv_values)
        )

        return future_income_pv

    def get_total_portfolio(self, state: State, discount_rate_annual: float) -> float:
        """Calculate total portfolio value (future income PV + current net worth).

        Args:
            state: Current simulation state
            discount_rate_annual: Annual discount rate for NPV calculation

        Returns:
            Total portfolio value (PV of future income + current net worth)
        """
        future_income_pv = self.get_future_income_pv(
            state=state, discount_rate_annual=discount_rate_annual
        )
        return future_income_pv + state.net_worth
