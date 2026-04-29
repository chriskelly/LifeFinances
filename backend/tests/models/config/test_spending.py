"""Testing for models/config/spending.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest
from pydantic import ValidationError

from app.models.config import SpendingProfile, _spending_profiles_validation
from app.models.config.spending import (
    InflationFollowingConfig,
    SpendingStrategyOptions,
)


class TestSpendingProfileValidation:
    """Test spending profile validation logic (existing tests)"""

    profile1 = SpendingProfile(yearly_amount=10000, end_date=1)
    profile2 = SpendingProfile(yearly_amount=20000, end_date=2)
    profile3 = SpendingProfile(yearly_amount=30000)

    def test_profiles_not_in_order(self):
        """Spending profiles must be in order"""
        profiles = [self.profile2, self.profile1, self.profile3]
        with pytest.raises(ValueError, match="must be in order"):
            _spending_profiles_validation(profiles)

    def test_last_profile_has_end_date(self):
        """The last spending profile must not have an end_date"""
        profiles = [self.profile1, self.profile2]
        with pytest.raises(ValueError, match="should have no end date"):
            _spending_profiles_validation(profiles)

    def test_valid_profiles(self):
        """Valid profiles should pass"""
        profiles = [self.profile1, self.profile2, self.profile3]
        _spending_profiles_validation(profiles)

    def test_empty_profiles_list(self):
        """Empty profiles list should raise error"""
        with pytest.raises(
            ValueError, match="At least one spending profile is required"
        ):
            _spending_profiles_validation([])

    def test_single_profile_with_end_date(self):
        """Single profile with end_date should fail"""
        profiles = [self.profile1]
        with pytest.raises(ValueError, match="should have no end date"):
            _spending_profiles_validation(profiles)

    def test_single_profile_without_end_date(self):
        """Single profile without end_date should pass"""
        profiles = [self.profile3]
        _spending_profiles_validation(profiles)

    def test_middle_profile_missing_end_date(self):
        """Middle profiles must have end_date"""
        profile_no_date = SpendingProfile(yearly_amount=15000, end_date=None)
        profiles = [self.profile1, profile_no_date, self.profile3]
        with pytest.raises(ValueError, match="must have an end_date"):
            _spending_profiles_validation(profiles)


class TestInflationFollowingConfig:
    """Test InflationFollowingConfig validation (T012)"""

    def test_valid_config(self, sample_spending_profiles):
        """Valid config with profiles should pass"""
        config = InflationFollowingConfig(
            chosen=True, profiles=sample_spending_profiles
        )
        assert config.chosen is True
        assert len(config.profiles) == len(sample_spending_profiles)
        assert (
            config.profiles[0].yearly_amount
            == sample_spending_profiles[0].yearly_amount
        )
        assert config.profiles[-1].end_date == sample_spending_profiles[-1].end_date

    def test_config_validates_profiles(self):
        """Config should delegate profile validation"""
        # Empty profiles should fail
        with pytest.raises(ValidationError) as exc_info:
            InflationFollowingConfig(chosen=True, profiles=[])
        assert "At least one spending profile is required" in str(exc_info.value)

    def test_config_validates_profile_order(self):
        """Config should validate chronological ordering"""
        profiles = [
            SpendingProfile(yearly_amount=70, end_date=2040.0),
            SpendingProfile(yearly_amount=60, end_date=2035.0),  # Out of order!
            SpendingProfile(yearly_amount=55, end_date=None),
        ]
        with pytest.raises(ValidationError) as exc_info:
            InflationFollowingConfig(chosen=True, profiles=profiles)
        assert "must be in order" in str(exc_info.value)

    def test_config_validates_last_profile_end_date(self):
        """Config should validate last profile has no end_date"""
        profiles = [
            SpendingProfile(yearly_amount=60, end_date=2035.0),
            SpendingProfile(yearly_amount=70, end_date=2040.0),  # Last has end_date!
        ]
        with pytest.raises(ValidationError) as exc_info:
            InflationFollowingConfig(chosen=True, profiles=profiles)
        assert "should have no end date" in str(exc_info.value)

    def test_config_inherits_from_strategy_config(self):
        """Config should inherit chosen and enabled from StrategyConfig"""
        from app.models.config.strategy import StrategyConfig

        config = InflationFollowingConfig(
            chosen=True,
            profiles=[SpendingProfile(yearly_amount=50, end_date=None)],
        )
        assert isinstance(config, StrategyConfig)
        assert config.chosen is True
        assert config.enabled is True  # Forced by chosen


class TestSpendingStrategyOptions:
    """Test SpendingStrategyOptions (T013)"""

    def test_default_inflation_following_chosen(self):
        """Default should have inflation_following chosen"""
        # Create with valid profiles
        profiles = [SpendingProfile(yearly_amount=60, end_date=None)]
        options = SpendingStrategyOptions(
            inflation_following=InflationFollowingConfig(chosen=True, profiles=profiles)
        )
        assert options.inflation_following.chosen is True

    def test_chosen_strategy_property(self, sample_spending_profiles):
        """Should return chosen strategy via chosen_strategy property"""
        options = SpendingStrategyOptions(
            inflation_following=InflationFollowingConfig(
                chosen=True, profiles=sample_spending_profiles
            )
        )
        strategy_name, strategy_obj = options.chosen_strategy
        assert strategy_name == "inflation_following"
        assert isinstance(strategy_obj, InflationFollowingConfig)
        assert strategy_obj.chosen is True
        assert len(strategy_obj.profiles) == len(sample_spending_profiles)

    def test_inherits_from_strategy_options(self):
        """Should inherit from StrategyOptions base class"""
        from app.models.config.strategy import StrategyOptions

        profiles = [SpendingProfile(yearly_amount=50, end_date=None)]
        options = SpendingStrategyOptions(
            inflation_following=InflationFollowingConfig(chosen=True, profiles=profiles)
        )
        assert isinstance(options, StrategyOptions)
        assert options.chosen_strategy is not None
