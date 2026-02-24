"""Testing for models/controllers/spending.py"""

# pyright: reportOptionalMemberAccess=false

import pytest

from app.data.constants import INTERVALS_PER_YEAR
from app.models.config.spending import (
    InflationFollowingConfig,
)
from app.models.config.user import User
from app.models.controllers.spending import _InflationFollowingStrategy


@pytest.fixture
def sample_state_early_date(sample_user: User):
    """Returns a State object with date in early profile period (2030.0)"""
    from app.models.financial.state import State

    return State(
        user=sample_user,
        date=2030.0,
        interval_idx=0,
        net_worth=250.0,
        inflation=1.05,
    )


@pytest.fixture
def sample_state_mid_date(sample_user: User):
    """Returns a State object with date in middle profile period (2038.0)"""
    from app.models.financial.state import State

    return State(
        user=sample_user,
        date=2038.0,
        interval_idx=0,
        net_worth=300.0,
        inflation=1.10,
    )


@pytest.fixture
def sample_state_late_date(sample_user: User):
    """Returns a State object with date in final profile period (2050.0)"""
    from app.models.financial.state import State

    return State(
        user=sample_user,
        date=2050.0,
        interval_idx=0,
        net_worth=400.0,
        inflation=1.15,
    )


@pytest.fixture
def sample_state_boundary_date(sample_user: User):
    """Returns a State object with date exactly on profile boundary (2035.25)"""
    from app.models.financial.state import State

    return State(
        user=sample_user,
        date=2035.25,
        interval_idx=0,
        net_worth=275.0,
        inflation=1.08,
    )


class TestInflationFollowingStrategy:
    """Test _InflationFollowingStrategy.calc_spending"""

    def test_calc_spending_early_profile(
        self, sample_state_early_date, sample_spending_profiles
    ):
        """Should select first profile for early date"""
        from app.models.controllers.spending import _InflationFollowingStrategy

        config = InflationFollowingConfig(
            chosen=True, profiles=sample_spending_profiles
        )
        strategy = _InflationFollowingStrategy(config=config)

        # date=2030.0, should use first profile (60K until 2035.25)
        spending = strategy.calc_spending(state=sample_state_early_date)

        # Expected: -(60 / 4) * 1.05 = -15.75
        expected = (
            -(sample_spending_profiles[0].yearly_amount / INTERVALS_PER_YEAR)
            * sample_state_early_date.inflation
        )
        assert spending == pytest.approx(expected)
        assert spending < 0  # Should be negative

    def test_calc_spending_mid_profile(
        self, sample_state_mid_date, sample_spending_profiles
    ):
        """Should select second profile for mid-range date"""
        from app.models.controllers.spending import _InflationFollowingStrategy

        config = InflationFollowingConfig(
            chosen=True, profiles=sample_spending_profiles
        )
        strategy = _InflationFollowingStrategy(config=config)

        # date=2038.0, should use second profile (70K until 2040.25)
        spending = strategy.calc_spending(state=sample_state_mid_date)

        # Expected: -(70 / 4) * 1.10 = -19.25
        expected = (
            -(sample_spending_profiles[1].yearly_amount / INTERVALS_PER_YEAR)
            * sample_state_mid_date.inflation
        )
        assert spending == pytest.approx(expected)

    def test_calc_spending_late_profile(
        self, sample_state_late_date, sample_spending_profiles
    ):
        """Should select final profile for late date"""
        from app.models.controllers.spending import _InflationFollowingStrategy

        config = InflationFollowingConfig(
            chosen=True, profiles=sample_spending_profiles
        )
        strategy = _InflationFollowingStrategy(config=config)

        # date=2050.0, should use third profile (55K indefinitely)
        spending = strategy.calc_spending(state=sample_state_late_date)

        # Expected: -(55 / 4) * 1.15 = -15.8125
        expected = (
            -(sample_spending_profiles[2].yearly_amount / INTERVALS_PER_YEAR)
            * sample_state_late_date.inflation
        )
        assert spending == pytest.approx(expected)

    def test_calc_spending_boundary_date(
        self, sample_state_boundary_date, sample_spending_profiles
    ):
        """Should use current profile when date equals end_date (date <= end_date)"""

        config = InflationFollowingConfig(
            chosen=True, profiles=sample_spending_profiles
        )
        strategy = _InflationFollowingStrategy(config=config)

        # date=2035.25, exactly at first profile boundary
        # Should still use first profile (60K) per clarification
        spending = strategy.calc_spending(state=sample_state_boundary_date)

        # Expected: -(60 / 4) * 1.08 = -16.2
        expected = (
            -(sample_spending_profiles[0].yearly_amount / INTERVALS_PER_YEAR)
            * sample_state_boundary_date.inflation
        )
        assert spending == pytest.approx(expected)

    def test_strategy_post_init_extracts_profiles(self, sample_spending_profiles):
        """Strategy __post_init__ should extract profiles from config"""
        from app.models.controllers.spending import _InflationFollowingStrategy

        config = InflationFollowingConfig(
            chosen=True, profiles=sample_spending_profiles
        )
        strategy = _InflationFollowingStrategy(config=config)

        assert strategy.profiles == sample_spending_profiles
        assert len(strategy.profiles) == len(sample_spending_profiles)


class TestSpendingController:
    """Test Controller initialization and delegation"""

    def test_controller_init_inflation_following(
        self, sample_user, sample_spending_profiles
    ):
        """Controller should initialize with inflation_following strategy"""
        from app.models.controllers.spending import Controller

        # Update sample_user to use new spending_strategy format
        user_dict = sample_user.model_dump()
        user_dict["spending_strategy"] = {
            "inflation_following": {
                "chosen": True,
                "profiles": sample_spending_profiles,
            }
        }
        test_user = User(**user_dict)

        controller = Controller(user=test_user)

        # Controller should have selected the inflation_following strategy
        assert controller._strategy is not None
        assert isinstance(controller._strategy, _InflationFollowingStrategy)

    def test_controller_init_invalid_strategy(self, sample_user):
        """Controller should raise error for invalid strategy name"""
        from pydantic import ValidationError

        # Create a user with an unsupported strategy (simulated)
        user_dict = sample_user.model_dump()
        user_dict["spending_strategy"] = {"invalid_strategy": {"chosen": True}}

        # This should fail validation (no strategy chosen)
        with pytest.raises((ValidationError, ValueError)):
            User(**user_dict)
