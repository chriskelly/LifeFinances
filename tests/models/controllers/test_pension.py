"""Testing for models/controllers/pension.py"""

# pylint:disable=missing-class-docstring,protected-access

import pytest
from app.data.constants import INTERVALS_PER_YEAR
from app.models.config import (
    IncomeProfile,
    NetWorthStrategyConfig,
    PensionOptions,
    User,
)
from app.models.controllers.pension import (
    LATE_YEAR,
    _AgeStrategy,
    BENEFIT_RATES,
    EARLY_YEAR,
    MID_YEAR,
    _CashOutStrategy,
    _NetWorthStrategy,
    Controller,
)
from app.models.financial.state import State


def test_age_strategy(first_state: State):
    """Should return 0 if date is before trigger date, and
    should return base * benefit_rate * inflation if date is
    after trigger date"""
    base = 100
    strategy = _AgeStrategy(trigger_year=MID_YEAR, base=base)
    first_state.date = EARLY_YEAR
    assert strategy.calc_payment(first_state) == 0
    first_state.date = MID_YEAR
    assert strategy.calc_payment(first_state) == pytest.approx(
        base * BENEFIT_RATES[MID_YEAR]
    )
    first_state.inflation = 2
    assert strategy.calc_payment(first_state) == pytest.approx(
        base * BENEFIT_RATES[MID_YEAR] * 2
    )


class TestNetWorthStrategy:
    @pytest.fixture
    def net_worth_strategy(self):
        """Sample _NetWorthStrategy with base=100 and net_worth_target=1000"""
        config = NetWorthStrategyConfig(net_worth_target=1000, chosen=True)
        return _NetWorthStrategy(config=config, base=100)

    def test_calc_payment_when_payment_exists(
        self, first_state: State, net_worth_strategy: _NetWorthStrategy
    ):
        """Should return payment x inflation if payment exists"""
        net_worth_strategy._payment = 300  # Simulate an existing payment
        first_state.inflation = 2
        result = net_worth_strategy.calc_payment(first_state)
        assert result == pytest.approx(600)

    def test_calc_payment_before_early_year(
        self, first_state: State, net_worth_strategy: _NetWorthStrategy
    ):
        """Should return 0 if date is before EARLY_YEAR"""
        first_state.date = EARLY_YEAR - 1
        payment = net_worth_strategy.calc_payment(first_state)
        assert payment == 0

    def test_calc_payment_below_net_worth_target(
        self, first_state: State, net_worth_strategy: _NetWorthStrategy
    ):
        """Should return payment if net worth is below net worth target"""
        first_state.date = EARLY_YEAR  # Date needs to be at least EARLY_YEAR
        first_state.net_worth = 0.9 * net_worth_strategy._net_worth_target
        payment = net_worth_strategy.calc_payment(first_state)
        assert payment == pytest.approx(
            BENEFIT_RATES[EARLY_YEAR] * net_worth_strategy._base
        )

    def test_calc_payment_above_net_worth_target(
        self, first_state: State, net_worth_strategy: _NetWorthStrategy
    ):
        """Should return 0 if net worth is above net worth target"""
        first_state.date = EARLY_YEAR  # Date needs to be at least EARLY_YEAR
        first_state.net_worth = 1.1 * net_worth_strategy._net_worth_target
        payment = net_worth_strategy.calc_payment(first_state)
        assert payment == pytest.approx(0)

    def test_calc_payment_late_year(
        self, first_state: State, net_worth_strategy: _NetWorthStrategy
    ):
        """Should return payment if it's LATE_YEAR"""
        first_state.date = LATE_YEAR
        payment = net_worth_strategy.calc_payment(first_state)
        assert payment == pytest.approx(
            BENEFIT_RATES[LATE_YEAR] * net_worth_strategy._base
        )


class TestCashOutStrategy:
    @pytest.fixture
    def cash_out_strategy(self, sample_user: User):
        """Sample _CashOutStrategy based on `sample_configs/full_config.yml`"""
        return _CashOutStrategy(user=sample_user)

    def test_calc_est_prev_interval_income(self, cash_out_strategy: _CashOutStrategy):
        """Ensure the _calc_est_prev_interval_income method provides the correct value"""
        assert cash_out_strategy._calc_est_prev_interval_income() == pytest.approx(
            24.04, 0.1
        )

    def test_calc_pension_balance(self, cash_out_strategy: _CashOutStrategy):
        """Ensure the _calc_pension_balance method provides the correct value"""
        assert cash_out_strategy._calc_pension_balance() == pytest.approx(172.84, 0.1)

    def test_intervals_between(self, cash_out_strategy: _CashOutStrategy):
        """_intervals_between should return the correct number of intervals between
        two dates regardless of the order of the dates"""
        date1 = 2023
        date2 = 2024
        assert cash_out_strategy._intervals_between(date1, date2) == INTERVALS_PER_YEAR
        assert cash_out_strategy._intervals_between(date2, date1) == INTERVALS_PER_YEAR

    def test_calc_payment(
        self, cash_out_strategy: _CashOutStrategy, first_state: State, sample_user: User
    ):
        """Integration test to ensure return value is consistent. Should return 0 if
        date is before or after the last date in the income profile."""
        first_state.date = sample_user.partner.income_profiles[0].last_date
        assert cash_out_strategy.calc_payment(first_state) == pytest.approx(172.84, 0.1)
        first_state.date += 1
        assert cash_out_strategy.calc_payment(first_state) == 0
        first_state.date -= 2
        assert cash_out_strategy.calc_payment(first_state) == 0


class TestController:
    class TestCalcBase:
        def test_sample_user(self, sample_user: User):
            """Should return the correct base value"""
            assert Controller._calc_base(
                sample_user.partner.income_profiles
            ) == pytest.approx(481.25, 0.1)

    class TestCalcYearsOnBreak:
        def test_base_case(self):
            """Should return the correct number of years on break"""
            job_breaks = [(2000, 2002), (2005, 2007), (2010, 2011)]
            assert Controller._calc_years_on_break(job_breaks) == 5

        def test_empty_list(self):
            """Should return 0 if the job_breaks list is empty"""
            job_breaks = []
            assert Controller._calc_years_on_break(job_breaks) == 0

        def test_single_break(self):
            """Should return the duration of a single job break"""
            job_breaks = [(2000, 2006)]
            assert Controller._calc_years_on_break(job_breaks) == 6

    class TestYearsLeftToWork:
        current_date = 2021

        def test_base_case(self):
            """Should return the correct number of years left to work"""
            income_profiles = [
                IncomeProfile(starting_income=1000, last_date=2022),
                IncomeProfile(starting_income=2000, last_date=2024),
                IncomeProfile(starting_income=3000, last_date=2026),
            ]
            assert (
                Controller._years_left_to_work(income_profiles, self.current_date) == 5
            )

        def test_with_zero_starting_income(self):
            """Should not count years with zero starting income"""
            income_profiles = [
                IncomeProfile(starting_income=0, last_date=2022),
                IncomeProfile(starting_income=2000, last_date=2024),
                IncomeProfile(starting_income=3000, last_date=2026),
            ]
            assert (
                Controller._years_left_to_work(income_profiles, self.current_date) == 4
            )

        def test_with_empty_income_profiles(self):
            """Should return 0 if the income_profiles list is empty"""
            income_profiles = []
            assert (
                Controller._years_left_to_work(income_profiles, self.current_date) == 0
            )

    def test_gen_strategy(self, sample_user: User):
        """Ensure Controller.strategy has been set correctly"""
        sample_user.admin.pension.strategy = PensionOptions(
            **{"early": {"chosen": True}}
        )
        strategy = Controller(sample_user)._strategy
        assert isinstance(strategy, _AgeStrategy)
        assert strategy._trigger_date == EARLY_YEAR
        sample_user.admin.pension.strategy = PensionOptions(**{"mid": {"chosen": True}})
        strategy = Controller(sample_user)._strategy
        assert isinstance(strategy, _AgeStrategy)
        assert strategy._trigger_date == MID_YEAR
        sample_user.admin.pension.strategy = PensionOptions(
            **{"late": {"chosen": True}}
        )
        strategy = Controller(sample_user)._strategy
        assert isinstance(strategy, _AgeStrategy)
        assert strategy._trigger_date == LATE_YEAR
        sample_user.admin.pension.strategy = PensionOptions(
            **{"net_worth": {"chosen": True}}
        )
        assert isinstance(Controller(sample_user)._strategy, _NetWorthStrategy)
        sample_user.admin.pension.strategy = PensionOptions(
            **{"cash_out": {"chosen": True}}
        )
        assert isinstance(Controller(sample_user)._strategy, _CashOutStrategy)
        sample_user.admin = None
        assert Controller(sample_user)._strategy is None

    def test_calc_payment(self, sample_user: User, first_state: State):
        """Should return the strategy's calc_payment (adjusted by trust factor) result unless there
        is no admin, in which case it should return 0"""
        controller = Controller(sample_user)
        first_state.date = LATE_YEAR
        assert controller.calc_payment(first_state) == pytest.approx(
            controller._strategy.calc_payment(first_state) * sample_user.admin.pension.trust_factor
        )
        sample_user.admin = None
        assert Controller(sample_user).calc_payment(first_state) == 0
