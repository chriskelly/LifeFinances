"""Testing for models/financials/allocation.py"""

# pylint:disable=missing-class-docstring, redefined-outer-name, protected-access
# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import random
import pytest
from app.data import constants
from app.models.config import NetWorthStrategyConfig, SocialSecurity, User
from app.models.controllers.job_income import Income, Controller as IncomeController
from app.models.controllers.social_security import (
    EARLY_AGE,
    LATE_AGE,
    MID_AGE,
    _AgeStrategy,
    _IndividualController,
    _NetWorthStrategy,
    Controller,
    _add_income_to_earnings_record,
    _apply_pia_rates,
    _adjust_bend_points,
    _calc_aime,
    _calc_spousal_benefit,
    _constrain_earnings,
    _fill_in_missing_intervals,
    _gen_pia,
)
from app.models.financial.state import State


AGE = 40
"""Standard age for testing"""


@pytest.fixture(autouse=True)
def modify_constants_for_module():
    """Set constants to values that are easy/reliable to test with

    This is a fixture that is automatically used by all tests in this module.
    """
    # Store original values
    original_pia_rates_pension = constants.PIA_RATES_PENSION
    original_pia_rates = constants.PIA_RATES
    original_ss_bend_points = constants.SS_BEND_POINTS
    # Set new values
    constants.PIA_RATES_PENSION = [0.4, 0.32, 0.15]
    constants.PIA_RATES = [0.9, 0.32, 0.15]
    constants.SS_BEND_POINTS = [1, 6]
    yield
    # Restore original values
    constants.PIA_RATES_PENSION = original_pia_rates_pension
    constants.PIA_RATES = original_pia_rates
    constants.SS_BEND_POINTS = original_ss_bend_points


@pytest.fixture
def ss_config():
    """Sample config for SocialSecurity"""
    data = {
        "trust_factor": 0.8,
        "pension_eligible": False,
        "strategy": {
            "early": {"enabled": True, "chosen": False},
            "mid": {"enabled": True, "chosen": True},
            "late": {"enabled": True, "chosen": False},
            "net_worth": {"enabled": True, "chosen": False, "net_worth_target": 2800.0},
            "same": None,
        },
        "earnings_records": {2010: 75, 2011: 78},
    }
    return SocialSecurity(**data)


@pytest.fixture
def timeline():
    """Sample timeline of Incomes"""
    return [
        Income(
            date=(constants.TODAY_YR - 10) + i * constants.YEARS_PER_INTERVAL,
            amount=20 + i,
            social_security_eligible=True if i % 2 == 0 else False,
        )
        for i in range(10)
    ]


@pytest.fixture
def earnings_record():
    """Sample earnings record

    Earnings have to be relative to current year for tests
    to return the same values as time goes on. I think.
    """
    return {
        constants.TODAY_YR - 13: 75,
        constants.TODAY_YR - 12: 78,
        constants.TODAY_YR - 11: 80,
        constants.TODAY_YR - 10: 150,
        constants.TODAY_YR - 9: 175,
    }


@pytest.fixture
def sample_individual_controller(ss_config, timeline):
    """Sample individual controller"""
    return _IndividualController(ss_config=ss_config, timeline=timeline, age=AGE)


class TestGenPIA:
    bend_points = [1.0, 6.0, 8.0]
    earnings = list(range(40))

    def test_apply_pia_rates(self, ss_config: SocialSecurity):
        """PIA should match experimentally determined value"""
        pia = _apply_pia_rates(bend_points=self.bend_points, ss_config=ss_config)
        assert pia == pytest.approx(2.8)

    def test_apply_pia_rates_pension(self, ss_config: SocialSecurity):
        """PIA is reduced if pension eligible"""
        ss_config.pension_eligible = True
        pia = _apply_pia_rates(bend_points=self.bend_points, ss_config=ss_config)
        assert pia == pytest.approx(2.3)

    def test_apply_pia_rates_less_bend_points(self, ss_config: SocialSecurity):
        """Function should be compaitable with 1 & 2 bend points"""
        pia = _apply_pia_rates(bend_points=self.bend_points[:2], ss_config=ss_config)
        assert pia == pytest.approx(2.5)
        pia = _apply_pia_rates(bend_points=self.bend_points[:1], ss_config=ss_config)
        assert pia == pytest.approx(0.9)

    def test_adjust_bend_points(self):
        """Should trim off bend points higher than AIME"""
        bend_points = _adjust_bend_points(aime=0.5)
        assert bend_points == pytest.approx([0.5])
        bend_points = _adjust_bend_points(aime=2)
        assert bend_points == pytest.approx([1, 2])
        bend_points = _adjust_bend_points(aime=8)
        assert bend_points == pytest.approx([1, 6, 8])

    def test_calc_aime_less_than_35_years(self):
        """Given yearly earnings, aime is the monthly average
        of 35 years of income, including years with no income"""
        aime = _calc_aime(self.earnings[:10])
        assert pytest.approx(aime, 0.01) == sum(self.earnings[:10]) / 420

    def test_calc_aime_more_than_35_years(self):
        """Should sort the list of earnings and only average highest years"""
        shuffled_earnings = self.earnings.copy()
        random.shuffle(shuffled_earnings)
        aime = _calc_aime(shuffled_earnings)
        assert pytest.approx(aime, 0.01) == sum(self.earnings[-35:]) / 420

    def test_gen_pia(self, ss_config: SocialSecurity):
        """PIA should be the product of the PIA rates and the AIME"""
        pia = _gen_pia(earnings=self.earnings, ss_config=ss_config)
        assert pia == pytest.approx(1.166, 0.01)


class TestGenEarnings:
    max_earnings = 100.0
    index = 1.2

    @pytest.fixture(autouse=True)
    def mock_extrapolators(self, monkeypatch: pytest.MonkeyPatch):
        """Mock extrapolators to return deterministic values for testing"""

        # Mock max_earnings_extrapolator to return a constant value
        def mock_max_earnings(_year: float) -> float:
            return self.max_earnings

        # Mock index_extrapolator to return 1.0 (no indexing)
        def mock_index(_year: float) -> float:
            return self.index

        # Patch in the module where they're imported and used
        monkeypatch.setattr(
            "app.models.controllers.social_security.max_earnings_extrapolator",
            mock_max_earnings,
        )
        monkeypatch.setattr(
            "app.models.controllers.social_security.index_extrapolator", mock_index
        )

    def test_constrain_earnings(self, earnings_record):
        """Should constrain earnings to the max earnings for each year"""
        earnings = _constrain_earnings(earnings_record)

        for earning in earnings:
            assert (
                earning <= self.max_earnings * self.index
            ), "Earnings should be constrained to max"

    def test_add_income_to_earnings_record(self, timeline, earnings_record):
        """Should add income to earnings record"""
        _add_income_to_earnings_record(
            timeline=timeline, earnings_record=earnings_record
        )
        expected_earnings_record = {
            constants.TODAY_YR - 13: 75,
            constants.TODAY_YR - 12: 78,
            constants.TODAY_YR - 11: 80,
            constants.TODAY_YR - 10: 236,
            constants.TODAY_YR - 9: 277,
            constants.TODAY_YR - 8: 57,
        }
        # test that expected_earnings_record and self.earnings_record are equal
        assert expected_earnings_record == earnings_record

    def test_fill_in_missing_intervals_doesnt_change_input(self, timeline):
        """Should not change the input timeline"""
        original_timeline = timeline.copy()
        _ = _fill_in_missing_intervals(timeline)
        assert original_timeline == timeline

    def test_fill_in_missing_intervals_no_changes_needed(self, timeline):
        """Should not change if timeline starts and ends on a full year"""
        new_timeline = _fill_in_missing_intervals(timeline[:8])
        assert new_timeline == timeline[:8]

    def test_fill_in_missing_intervals(self, timeline):
        """Should fill in missing intervals"""
        new_timeline = _fill_in_missing_intervals(timeline[2:])
        assert len(new_timeline) == 12
        assert new_timeline[0].date == pytest.approx(constants.TODAY_YR - 10)
        assert new_timeline[-1].date == pytest.approx(constants.TODAY_YR - 7.25)


class TestAgeStrategy:
    age_strategy = _AgeStrategy(pia=1, ss_age=EARLY_AGE, current_age=AGE)

    def test_calc_payment_before_ss_age(self, first_state: State):
        """Should not give payment before SS age"""
        payment = self.age_strategy.calc_payment(state=first_state)
        assert payment == 0

    def test_calc_payment_after_ss_age(self, first_state: State):
        """Should give payment after SS age"""
        first_state.date = constants.TODAY_YR + EARLY_AGE - AGE + 1
        payment = self.age_strategy.calc_payment(state=first_state)
        assert payment > 0


class TestNetWorthStrategy:
    config = NetWorthStrategyConfig(net_worth_target=1000)
    strategy = _NetWorthStrategy(config=config, pia=1, current_age=AGE)

    def test_calc_payment_before_early_age(self, first_state: State):
        """Should not give payment before SS date"""
        first_state.date = constants.TODAY_YR
        payment = self.strategy.calc_payment(state=first_state)
        assert payment == 0

    def test_calc_payment_before_late_over_target(self, first_state: State):
        """Should give payment after net worth target met"""
        first_state.date = (
            constants.TODAY_YR + EARLY_AGE - self.strategy._current_age + 1
        )
        first_state.net_worth = self.config.net_worth_target * first_state.inflation - 1
        payment = self.strategy.calc_payment(state=first_state)
        assert payment > 0

    def test_calc_payment_after_late_under_target(self, first_state: State):
        """Should give payment after late date even if net worth target not met"""
        first_state.date = constants.TODAY_YR + LATE_AGE - self.strategy._current_age
        payment = self.strategy.calc_payment(state=first_state)
        assert payment > 0


class TestSpousalBenefits:
    def test_calc_spousal_benefit_worker_triggered_spouse_not(
        self, sample_individual_controller, ss_config, timeline, first_state: State
    ):
        """Benefit should be 0 when spouse's social security not triggered"""
        worker_controller = sample_individual_controller
        # create younger spouse
        spousal_controller = _IndividualController(
            ss_config=ss_config,
            timeline=timeline,
            age=AGE - 5,
        )
        first_state.date = constants.TODAY_YR + MID_AGE - AGE + 1
        benefit = _calc_spousal_benefit(
            worker_controller=worker_controller,
            spousal_controller=spousal_controller,
            state=first_state,
        )
        assert benefit == 0

    def test_calc_spousal_benefit_spouse_triggered_worker_not(
        self, sample_individual_controller, ss_config, timeline, first_state: State
    ):
        """Benefit should be 0 when worker's social security not triggered"""
        worker_controller = sample_individual_controller
        # create older spouse
        spousal_controller = _IndividualController(
            ss_config=ss_config,
            timeline=timeline,
            age=AGE + 5,
        )
        first_state.date = constants.TODAY_YR + MID_AGE - AGE
        benefit = _calc_spousal_benefit(
            worker_controller=worker_controller,
            spousal_controller=spousal_controller,
            state=first_state,
        )
        assert benefit == 0

    def test_calc_spousal_benefit_both_triggered(
        self, sample_individual_controller, first_state: State
    ):
        """Benefit should be correct when both have triggered social security"""
        worker_controller = sample_individual_controller
        # create older spouse
        spousal_controller = sample_individual_controller
        first_state.date = constants.TODAY_YR + MID_AGE - AGE + 1
        benefit = _calc_spousal_benefit(
            worker_controller=worker_controller,
            spousal_controller=spousal_controller,
            state=first_state,
        )
        assert benefit == pytest.approx(1.08, 0.1)


def test_controller_calc_payment(sample_user: User, first_state: State):
    """Should return the roughly correct payment. Fragile, but can be a sanity check."""
    trust_factor = sample_user.social_security_pension.trust_factor
    if trust_factor is None:
        raise ValueError("trust_factor cannot be None")
    controller = Controller(
        user_config=sample_user, income_controller=IncomeController(sample_user)
    )
    first_state.date = constants.TODAY_YR + MID_AGE - sample_user.age + 1
    payment = controller.calc_payment(state=first_state)
    expected_user_payment = 4.65 * trust_factor
    expected_partner_payment = 2.32 * trust_factor
    assert payment == pytest.approx(
        [expected_user_payment, expected_partner_payment], 0.3
    )
