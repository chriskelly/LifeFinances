"""Testing for models/controllers/future_income.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import copy

import numpy as np
import pytest
from pytest_mock.plugin import MockerFixture

from app.data import constants
from app.models.config import IncomeProfile, User
from app.models.controllers.economic_data import EconomicStateData
from app.models.controllers.future_income import Controller as FutureIncomeController
from app.models.controllers.job_income import Controller as JobIncomeController
from app.models.financial.state import gen_first_state

# Test constants for predictable income scenarios
YEARLY_INCOME = 100  # $100k/year (in thousands)
INCOME_DURATION_YEARS = 10.0
INTERVALS_PER_YEAR = constants.INTERVALS_PER_YEAR
JOB_INCOME_PER_INTERVAL = YEARLY_INCOME / INTERVALS_PER_YEAR

# Benefit amounts for testing
SS_USER_BENEFIT = 5  # $5k per interval
SS_PARTNER_BENEFIT = 3  # $3k per interval
PENSION_BENEFIT = 2  # $2k per interval
TOTAL_BENEFITS = SS_USER_BENEFIT + SS_PARTNER_BENEFIT + PENSION_BENEFIT
BENEFITS_START_INTERVAL = 20


@pytest.fixture
def user_with_job_income(sample_user: User) -> User:
    """User with simple job income profile based on sample_user"""
    user = copy.deepcopy(sample_user)
    # Clear partner to have predictable single-income scenario
    user.partner = None
    # Clear existing income profiles and set simple, predictable income
    user.income_profiles = [
        IncomeProfile(
            starting_income=YEARLY_INCOME,
            last_date=constants.TODAY_YR_QT + INCOME_DURATION_YEARS,
            yearly_raise=0.0,  # No raises for predictable testing
        )
    ]
    return user


@pytest.fixture
def user_no_income(sample_user: User) -> User:
    """User with no income based on sample_user"""
    user = copy.deepcopy(sample_user)
    user.partner = None  # Remove partner
    user.income_profiles = None  # Completely remove income profiles
    return user


@pytest.fixture
def controller_factory(mocker: MockerFixture):
    """Factory to create FutureIncomeController with mocked dependencies"""

    def _create_controller(
        user: User,
        *,
        social_security_payments: list[tuple[float, float]] | None = None,
        pension_payments: list[float] | None = None,
        inflation_values: list[float] | None = None,
    ) -> FutureIncomeController:
        """Create FutureIncomeController with configurable mocks.

        Args:
            user: User configuration
            social_security_payments: List of (user_payment, partner_payment) tuples per interval
            pension_payments: List of pension payments per interval
            inflation_values: List of inflation values per interval

        Returns:
            FutureIncomeController instance
        """
        # Create real job income controller
        job_income_controller = JobIncomeController(user)

        # Mock social security controller
        if social_security_payments is None:
            social_security_payments = [(0.0, 0.0)] * user.intervals_per_trial

        social_security_controller = mocker.MagicMock()

        def _calc_ss_payment(state):
            # Use index-based access instead of iterator to allow recalculation
            return social_security_payments[state.interval_idx]

        social_security_controller.calc_payment = mocker.Mock(
            side_effect=_calc_ss_payment
        )

        # Mock pension controller
        if pension_payments is None:
            pension_payments = [0.0] * user.intervals_per_trial

        pension_controller = mocker.MagicMock()

        def _calc_pension_payment(state):
            # Use index-based access instead of iterator to allow recalculation
            return pension_payments[state.interval_idx]

        pension_controller.calc_payment = mocker.Mock(side_effect=_calc_pension_payment)

        # Mock economic data controller
        if inflation_values is None:
            inflation_values = [1.0] * user.intervals_per_trial

        economic_data_controller = mocker.MagicMock()

        def _get_economic_state_data(interval_idx: int) -> EconomicStateData:
            return EconomicStateData(
                asset_rates=np.array([]),
                inflation=inflation_values[interval_idx],
                asset_lookup={},
            )

        economic_data_controller.get_economic_state_data = mocker.Mock(
            side_effect=_get_economic_state_data
        )

        # Create FutureIncomeController
        return FutureIncomeController(
            user=user,
            job_income_controller=job_income_controller,
            social_security_controller=social_security_controller,
            pension_controller=pension_controller,
            economic_data_controller=economic_data_controller,
        )

    return _create_controller


class TestControllerInitialization:
    """Test FutureIncomeController initialization and lazy computation"""

    def test_initialization_does_not_compute_income(
        self, user_with_job_income: User, controller_factory
    ):
        """Controller should initialize without computing income arrays (lazy)"""
        controller = controller_factory(user_with_job_income)

        # Arrays should be None initially (lazy computation)
        assert controller.get_future_income_by_interval() is None

    def test_initialization_stores_dependencies(
        self, user_with_job_income: User, controller_factory, mocker: MockerFixture
    ):
        """Controller should store all dependency controllers"""
        controller = controller_factory(user_with_job_income)

        # Should have stored user and controllers
        assert controller._user == user_with_job_income
        assert controller._job_income_controller is not None
        assert controller._social_security_controller is not None
        assert controller._pension_controller is not None
        assert controller._economic_data_controller is not None


class TestComputeFutureIncome:
    """Test explicit computation of future income arrays"""

    def test_compute_future_income_creates_arrays(
        self, user_with_job_income: User, controller_factory
    ):
        """compute_future_income should create job, benefit, and total income arrays"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        controller.compute_future_income(state=state)

        income_array = controller.get_future_income_by_interval()
        assert income_array is not None
        assert len(income_array) == user_with_job_income.intervals_per_trial
        assert isinstance(income_array, np.ndarray)

    def test_compute_future_income_with_job_only(
        self, user_with_job_income: User, controller_factory
    ):
        """Should correctly compute income from job income only"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        controller.compute_future_income(state=state)

        income_array = controller.get_future_income_by_interval()
        assert income_array is not None

        # First interval should have job income
        assert income_array[0] == pytest.approx(JOB_INCOME_PER_INTERVAL)
        # Income continues for duration (check last expected interval has income)
        expected_intervals = int(INCOME_DURATION_YEARS * INTERVALS_PER_YEAR)
        assert income_array[min(expected_intervals - 1, len(income_array) - 1)] > 0

    def test_compute_future_income_with_benefits(
        self, user_with_job_income: User, controller_factory
    ):
        """Should include social security and pension in future income"""
        # Set up benefits starting at BENEFITS_START_INTERVAL
        intervals_before_benefits = BENEFITS_START_INTERVAL
        intervals_with_benefits = (
            user_with_job_income.intervals_per_trial - BENEFITS_START_INTERVAL
        )

        ss_payments = [(0.0, 0.0)] * intervals_before_benefits + [
            (SS_USER_BENEFIT, SS_PARTNER_BENEFIT)
        ] * intervals_with_benefits
        pension_payments = [0.0] * intervals_before_benefits + [
            PENSION_BENEFIT
        ] * intervals_with_benefits

        controller = controller_factory(
            user_with_job_income,
            social_security_payments=ss_payments,
            pension_payments=pension_payments,
        )
        state = gen_first_state(user_with_job_income)

        controller.compute_future_income(state=state)

        income_array = controller.get_future_income_by_interval()
        assert income_array is not None

        # Before benefits: job income only
        assert income_array[0] == pytest.approx(JOB_INCOME_PER_INTERVAL)
        assert income_array[BENEFITS_START_INTERVAL - 1] == pytest.approx(
            JOB_INCOME_PER_INTERVAL
        )

        # After benefits start: job + SS + pension (at benefit start interval)
        expected_with_benefits = JOB_INCOME_PER_INTERVAL + TOTAL_BENEFITS
        assert income_array[BENEFITS_START_INTERVAL] == pytest.approx(
            expected_with_benefits
        )
        # Note: At end of trial, job income may have ended but benefits continue
        # So we just check that benefits are present
        assert income_array[-1] >= TOTAL_BENEFITS

    def test_compute_future_income_no_income(
        self, user_no_income: User, controller_factory
    ):
        """Should handle user with no income sources"""
        controller = controller_factory(user_no_income)
        state = gen_first_state(user_no_income)

        controller.compute_future_income(state=state)

        income_array = controller.get_future_income_by_interval()
        assert income_array is not None
        assert len(income_array) == user_no_income.intervals_per_trial
        # All zeros
        assert np.allclose(income_array, 0.0)

    def test_compute_future_income_can_recalculate(
        self, user_with_job_income: User, controller_factory
    ):
        """compute_future_income should allow recalculation with different state"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        # First computation
        controller.compute_future_income(state=state)
        first_array = controller.get_future_income_by_interval()
        assert first_array is not None

        # Recalculation should work (same result in this case)
        controller.compute_future_income(state=state)
        second_array = controller.get_future_income_by_interval()
        assert second_array is not None
        assert np.array_equal(first_array, second_array)


class TestGetFutureIncomePV:
    """Test present value calculation of future income"""

    def test_lazy_computation_on_first_call(
        self, user_with_job_income: User, controller_factory
    ):
        """get_future_income_pv should trigger lazy computation on first call"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        # Arrays should be None before first call
        assert controller.get_future_income_by_interval() is None

        # Calculate PV (should trigger computation)
        pv = controller.get_future_income_pv(state=state, discount_rate_annual=0.05)

        # Arrays should now be computed
        assert controller.get_future_income_by_interval() is not None
        assert pv > 0

    def test_pv_with_zero_discount_rate(
        self, user_with_job_income: User, controller_factory
    ):
        """PV with zero discount rate should equal sum of future income"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        pv = controller.get_future_income_pv(state=state, discount_rate_annual=0.0)

        # With zero discount, PV = sum of all future income
        # Starting from interval 1 (next interval), not current
        total_intervals = int(INCOME_DURATION_YEARS * INTERVALS_PER_YEAR)
        future_intervals = total_intervals - 1  # Exclude current interval
        expected_pv = JOB_INCOME_PER_INTERVAL * future_intervals

        assert pv == pytest.approx(expected_pv, rel=0.05)

    def test_pv_decreases_with_higher_discount_rate(
        self, user_with_job_income: User, controller_factory
    ):
        """Higher discount rates should result in lower present values"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        pv_low = controller.get_future_income_pv(state=state, discount_rate_annual=0.02)

        # Need to recalculate or use new controller for different rate
        controller2 = controller_factory(user_with_job_income)
        pv_high = controller2.get_future_income_pv(
            state=state, discount_rate_annual=0.10
        )

        assert pv_low > pv_high

    def test_pv_at_later_interval(self, user_with_job_income: User, controller_factory):
        """PV should decrease as we move forward in time (fewer future payments)"""
        controller = controller_factory(user_with_job_income)

        state_0 = gen_first_state(user_with_job_income)
        pv_0 = controller.get_future_income_pv(state=state_0, discount_rate_annual=0.05)

        # Create state at interval 20 (halfway through)
        state_20 = copy.deepcopy(state_0)
        state_20.interval_idx = 20

        controller2 = controller_factory(user_with_job_income)
        pv_20 = controller2.get_future_income_pv(
            state=state_20, discount_rate_annual=0.05
        )

        # PV at later interval should be less (fewer payments remaining)
        assert pv_20 < pv_0

    def test_pv_at_last_interval_is_zero(
        self, user_with_job_income: User, controller_factory
    ):
        """PV at last interval should be zero (no future income)"""
        controller = controller_factory(user_with_job_income)

        state = gen_first_state(user_with_job_income)
        # Move to last interval
        last_state = copy.deepcopy(state)
        last_state.interval_idx = user_with_job_income.intervals_per_trial - 1

        pv = controller.get_future_income_pv(
            state=last_state, discount_rate_annual=0.05
        )

        assert pv == pytest.approx(0.0)

    def test_pv_with_no_income(self, user_no_income: User, controller_factory):
        """PV should be zero when user has no income"""
        controller = controller_factory(user_no_income)
        state = gen_first_state(user_no_income)

        pv = controller.get_future_income_pv(state=state, discount_rate_annual=0.05)

        assert pv == pytest.approx(0.0)


class TestGetTotalPortfolio:
    """Test total portfolio calculation (PV of future income + net worth)"""

    def test_total_portfolio_includes_net_worth(
        self, user_with_job_income: User, controller_factory
    ):
        """Total portfolio should be sum of future income PV and current net worth"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        discount_rate = 0.05
        pv = controller.get_future_income_pv(
            state=state, discount_rate_annual=discount_rate
        )
        total = controller.get_total_portfolio(
            state=state, discount_rate_annual=discount_rate
        )

        # Total should equal PV + net_worth
        assert total == pytest.approx(pv + state.net_worth)

    def test_total_portfolio_with_zero_net_worth(
        self, user_with_job_income: User, controller_factory
    ):
        """Total portfolio should equal PV when net worth is zero"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)
        state.net_worth = 0.0

        discount_rate = 0.05
        pv = controller.get_future_income_pv(
            state=state, discount_rate_annual=discount_rate
        )
        total = controller.get_total_portfolio(
            state=state, discount_rate_annual=discount_rate
        )

        assert total == pytest.approx(pv)

    def test_total_portfolio_with_negative_net_worth(
        self, user_with_job_income: User, controller_factory
    ):
        """Total portfolio should handle negative net worth correctly"""
        controller = controller_factory(user_with_job_income)
        state = gen_first_state(user_with_job_income)

        negative_net_worth = -50.0
        state.net_worth = negative_net_worth

        discount_rate = 0.05
        pv = controller.get_future_income_pv(
            state=state, discount_rate_annual=discount_rate
        )
        total = controller.get_total_portfolio(
            state=state, discount_rate_annual=discount_rate
        )

        expected_total = pv + negative_net_worth
        assert total == pytest.approx(expected_total)

    def test_total_portfolio_no_income_no_savings(
        self, user_no_income: User, controller_factory
    ):
        """Total portfolio should be zero when no income and no savings"""
        controller = controller_factory(user_no_income)
        state = gen_first_state(user_no_income)
        state.net_worth = 0.0

        total = controller.get_total_portfolio(state=state, discount_rate_annual=0.05)

        assert total == pytest.approx(0.0)
