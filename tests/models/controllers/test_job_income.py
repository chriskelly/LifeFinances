"""Testing for models/financials/allocation.py"""
# pylint:disable=protected-access

import pytest
from app.data import constants
from app.models.config import User, IncomeProfile
from app.models.controllers.job_income import Controller


def test_job_income_controller(sample_user: User):
    """Test that the job income controller generates the correct income timeline

    Checks:
        income increments at the start of the new year
        income changes at the end date of the profile
    """
    constants.TODAY_YR_QT = (
        2000.5  # set the constant so that we start on a predicatable quarter
    )
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

    expected_user_income = [100.0, 100.0, 110.0, 110.0, 110.0, 200.0]
    expected_partner_income = [0.0, 0.0, 0.0, 0.0, 0.0, 150.0]
    expected_total_income = [
        user + partner
        for user, partner in zip(expected_user_income, expected_partner_income)
    ]
    expected_tax_deferred = [10.0, 10.0, 11.0, 11.0, 11.0, 45.0]
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
    assert len(controller.user_timeline) == sample_user.intervals_per_trial
    assert len(controller.partner_timeline) == sample_user.intervals_per_trial
