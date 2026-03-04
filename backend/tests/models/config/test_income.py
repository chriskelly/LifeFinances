"""Testing for models/config/income.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest

from app.models.config import IncomeProfile, _income_profiles_in_order


def test_income_profiles_in_order():
    """Income profiles must be in order"""
    profile1 = IncomeProfile(starting_income=10000, last_date=5)
    profile2 = IncomeProfile(starting_income=20000, last_date=3)
    profiles = [profile1, profile2]
    with pytest.raises(ValueError):
        _income_profiles_in_order(profiles)
