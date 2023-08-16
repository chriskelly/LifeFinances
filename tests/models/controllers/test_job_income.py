"""Testing for models/financials/allocation.py"""
# pylint:disable=protected-access

import pytest
from app.data import constants
from app.models.config import User, IncomeProfile
from app.models.controllers.job_income import Controller


def test_job_income_controller(sample_user: User):
    """Test that the job income controller generates the correct income timeline"""
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
    expected_user_timeline = [100.0, 100.0, 110.0, 110.0, 110.0, 200.0]
    expected_partner_timeline = [0.0, 0.0, 0.0, 0.0, 0.0, 150.0]
    expected_tax_deferred = [10.0, 10.0, 11.0, 11.0, 11.0, 45.0]
    assert controller._user[:6] == pytest.approx(expected_user_timeline)
    assert controller._partner[:6] == pytest.approx(expected_partner_timeline)
    assert controller._tax_deferred[:6] == pytest.approx(expected_tax_deferred)
    # Check the generated timelines are the correct size
    assert len(controller._user) == sample_user.intervals_per_trial
    assert len(controller._partner) == sample_user.intervals_per_trial
    assert len(controller._tax_deferred) == sample_user.intervals_per_trial
