"""Testing for models/config/spending.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest

from app.models.config import SpendingProfile, _spending_profiles_validation


class TestSpendingProfileValidation:
    profile1 = SpendingProfile(yearly_amount=10000, end_date=1)
    profile2 = SpendingProfile(yearly_amount=20000, end_date=2)
    profile3 = SpendingProfile(yearly_amount=30000)

    def test_profiles_not_in_order(self):
        """Spending profiles must be in order"""
        profiles = [self.profile2, self.profile1, self.profile3]
        with pytest.raises(ValueError):
            _spending_profiles_validation(profiles)

    def test_last_profile_has_end_date(self):
        """The last spending profile must not have an end_date"""
        profiles = [self.profile1, self.profile2]
        with pytest.raises(ValueError):
            _spending_profiles_validation(profiles)

    def test_valid_profiles(self):
        """Valid profiles should pass"""
        profiles = [self.profile1, self.profile2, self.profile3]
        _spending_profiles_validation(profiles)
