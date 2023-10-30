"""Testing for models/financials/allocation.py"""
# pylint:disable=protected-access,missing-class-docstring

import pytest
from app.data import constants
from app.models.config import User, IncomeProfile
from app.models.controllers.job_income import Controller


@pytest.fixture(autouse=True)
def fix_today_yr_qt():
    """set the constant so that we start on a predicatable quarter"""
    original_value = constants.TODAY_YR_QT
    constants.TODAY_YR_QT = 2000.5
    yield
    constants.TODAY_YR_QT = original_value


def test_job_income_controller(sample_user: User):
    """Test that the job income controller generates the correct income timeline

    Checks:
        income increments at the start of the new year
        income changes at the end date of the profile
    """
    user_income_profiles = [
        {
            "starting_income": 100,
            "tax_deferred_income": 10,
            "yearly_raise": 0.1,
            "last_date": constants.TODAY_YR_QT + 1,
        },
        {
            "starting_income": 200,
            "tax_deferred_income": 5,
            "yearly_raise": 0.1,
            "last_date": constants.TODAY_YR_QT + 2,
        },
    ]
    partner_income_profiles = [
        {
            "starting_income": 0,
            "tax_deferred_income": 0,
            "yearly_raise": 0,
            "last_date": constants.TODAY_YR_QT + 1,
        },
        {
            "starting_income": 150,
            "tax_deferred_income": 40,
            "yearly_raise": 0.1,
            "last_date": constants.TODAY_YR_QT + 2,
        },
    ]
    sample_user.income_profiles = [
        IncomeProfile(**user_income_profiles[0]),
        IncomeProfile(**user_income_profiles[1]),
    ]
    sample_user.partner.income_profiles = [
        IncomeProfile(**partner_income_profiles[0]),
        IncomeProfile(**partner_income_profiles[1]),
    ]
    controller = Controller(sample_user)

    expected_user_income = [25.0, 25.0, 27.5, 27.5, 27.5, 50.0]
    expected_partner_income = [0.0, 0.0, 0.0, 0.0, 0.0, 37.5]
    expected_total_income = [
        user + partner
        for user, partner in zip(expected_user_income, expected_partner_income)
    ]
    expected_tax_deferred = [2.5, 2.5, 2.75, 2.75, 2.75, 11.25]
    expected_taxable_income = [
        total - deferred
        for total, deferred in zip(expected_total_income, expected_tax_deferred)
    ]

    assert [controller.get_user_income(i) for i in range(6)] == pytest.approx(
        expected_user_income
    )
    assert [controller.get_partner_income(i) for i in range(6)] == pytest.approx(
        expected_partner_income
    )
    assert [controller.get_total_income(i) for i in range(6)] == pytest.approx(
        expected_total_income
    )
    assert [controller.get_taxable_income(i) for i in range(6)] == pytest.approx(
        expected_taxable_income
    )
    # Check the generated timelines are the correct size
    assert len(controller._user_timeline) == sample_user.intervals_per_trial
    assert len(controller._partner_timeline) == sample_user.intervals_per_trial


class TestIsWorking:
    user_working_years = 2
    partner_nonworking_years = 1
    partner_working_years = 2
    controller = None

    @pytest.fixture(autouse=True)
    def setup(self, sample_user: User):
        """Setup profiles and controller"""
        user_income_profiles = [
            {
                "starting_income": 100,
                "last_date": constants.TODAY_YR_QT + self.user_working_years,
            },
        ]
        partner_income_profiles = [
            {
                "starting_income": 0,
                "last_date": constants.TODAY_YR_QT + self.partner_nonworking_years,
            },
            {
                "starting_income": 100,
                "last_date": constants.TODAY_YR_QT
                + (self.partner_nonworking_years + self.partner_working_years),
            },
        ]
        sample_user.income_profiles = [
            IncomeProfile(**user_income_profiles[0]),
        ]
        sample_user.partner.income_profiles = [
            IncomeProfile(**partner_income_profiles[0]),
            IncomeProfile(**partner_income_profiles[1]),
        ]
        self.controller = Controller(sample_user)

    def test_when_user_working(self):
        """Should return True if the user is working during the given interval"""
        for i in range(self.user_working_years * constants.INTERVALS_PER_YEAR):
            assert self.controller.is_working(i) is True

    def test_when_partner_working(self):
        """Should return True if the partner is working during the given interval"""
        for i in range(
            self.partner_nonworking_years * constants.INTERVALS_PER_YEAR,
            (self.partner_nonworking_years + self.partner_working_years)
            * constants.INTERVALS_PER_YEAR,
        ):
            assert self.controller.is_working(i) is True

    def test_when_user_and_partner_not_working(self):
        """Should return False if neither the user nor the partner is working
        during the given interval"""
        first_interval_not_working = (
            1
            + max(
                self.user_working_years,
                self.partner_nonworking_years + self.partner_working_years,
            )
            * constants.INTERVALS_PER_YEAR
        )
        assert self.controller.is_working(first_interval_not_working) is False
