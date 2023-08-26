"""Testing for models/config.py
run `python3 -m pytest` if VSCode Testing won't load
"""
# pylint:disable=redefined-outer-name,missing-class-docstring,no-name-in-module

from typing import Optional
from dataclasses import dataclass
import yaml
import pytest
from pydantic import ValidationError
from app.data import constants
from app.models.config import (
    IncomeProfile,
    User,
    StrategyConfig,
    StrategyOptions,
    attribute_filller,
    _income_profiles_in_order,
)


def test_sample_config_data(sample_config_data):
    """Ensure sample data is valid"""
    assert sample_config_data
    try:
        user = User(**sample_config_data)
    except ValidationError as error:
        pytest.fail(f"Failed to validate sample user data: {error}")

    # If the config model is changed, but the sample_config isn't updated
    # correctly, this test should help capture undeclared objects
    exceptions = {"same", "equity_target"}

    def check_for_none(obj, parent_path=""):
        for key, value in obj.items():
            if value is None and key not in exceptions:
                pytest.fail(f"Value at path '{parent_path}.{key}' is None")
            elif isinstance(value, dict):
                check_for_none(value, parent_path=f"{parent_path}.{key}")

    check_for_none(user.model_dump())


def test_user_data():
    """Ensure user's data is valid"""
    with open(constants.CONFIG_PATH, "r", encoding="utf-8") as file:
        user_data = yaml.safe_load(file)
    assert user_data
    try:
        User(**user_data)
    except ValidationError as error:
        pytest.fail(f"Failed to validate user's data: {error}")


def test_sample_min_data():
    """Ensure sample min configs are valid"""
    for path in [
        constants.SAMPLE_MIN_CONFIG_INCOME_PATH,
        constants.SAMPLE_MIN_CONFIG_NET_WORTH_PATH,
    ]:
        with open(path, "r", encoding="utf-8") as file:
            user_data = yaml.safe_load(file)
        assert user_data
        try:
            User(**user_data)
        except ValidationError as error:
            pytest.fail(f"Failed to validate min config data: {error}")


def test_chosen_forces_enabled():
    """Any strategy with chosen=True should be enabled"""
    strategy = StrategyConfig(enabled=False, chosen=True)
    assert strategy.enabled is True


@pytest.fixture
def strategy_options() -> StrategyOptions:
    """Sample StrategyOptions"""

    data = {
        "strategy1": {"enabled": True},
        "strategy2": {"enabled": False},
        "strategy3": {"enabled": True, "chosen": True},
    }

    class MyOptions(StrategyOptions):
        strategy1: StrategyConfig
        strategy2: StrategyConfig
        strategy3: StrategyConfig

    my_options = MyOptions(**data)
    return my_options


def test_enabled_strategies(strategy_options: StrategyOptions):
    """All strategies with `enabled=True` in a StrategyOption instance
    should be included in the `enabled_strategies` property"""
    enabled_strategies = strategy_options.enabled_strategies
    assert len(enabled_strategies) == 2
    assert "strategy1" in enabled_strategies
    assert "strategy3" in enabled_strategies
    assert "strategy2" not in enabled_strategies


def test_chosen_strategy(strategy_options: StrategyOptions):
    """The strategy with `chosen=True` should
    be the `chosen_strategy` of a StrategyOption instance."""
    chosen_strategy = strategy_options.chosen_strategy
    assert chosen_strategy[0] == "strategy3"


def test_user_state_supported(sample_config_data):
    """If the user selects a state not supported,
    a ValidationError should be captured."""
    sample_config_data["state"] = "Mexico"
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**sample_config_data)


def test_attribute_filler():
    """The attribute_filler function should overwrite
    `None` values recursively, but not other values"""

    @dataclass
    class ThirdLevelObj:
        str1: Optional[str] = None
        str2: Optional[str] = None

    @dataclass
    class SecondLevelObj:
        third_lvl: ThirdLevelObj
        str1: Optional[str] = None

    @dataclass
    class FirstLevelObj:
        second_lvl: SecondLevelObj
        str1: Optional[str] = None

    # Test that it won't fill set values
    obj = FirstLevelObj(
        str1="World",
        second_lvl=SecondLevelObj(
            str1="World", third_lvl=ThirdLevelObj(str1="World", str2="World")
        ),
    )
    attribute_filller(obj=obj, attr="str1", fill_value="Hello")
    assert obj.str1 == "World"
    assert obj.second_lvl.third_lvl.str1 == "World"
    assert obj.second_lvl.third_lvl.str2 == "World"

    # Test that it will fill unspecified values
    obj = FirstLevelObj(second_lvl=SecondLevelObj(third_lvl=ThirdLevelObj()))
    attribute_filller(obj=obj, attr="str1", fill_value="Hello")
    assert obj.str1 == "Hello"
    assert obj.second_lvl.third_lvl.str1 == "Hello"
    assert obj.second_lvl.third_lvl.str2 is None


def test_income_profiles_in_order():
    """Income profiles must be in order"""
    profile1 = IncomeProfile(starting_income=10000, last_date=5)
    profile2 = IncomeProfile(starting_income=20000, last_date=3)
    profiles = [profile1, profile2]
    with pytest.raises(ValueError):
        _income_profiles_in_order(profiles)


def test_social_security_user_same_strategy(sample_config_data):
    """If the user enables the `same` strategy for social_security_pension,
    a ValidationError should be captured."""
    sample_config_data["social_security_pension"]["strategy"]["same"] = {
        "enabled": True
    }
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**sample_config_data)


def test_either_income_or_net_worth():
    """User should provide at least one income profile or net worth"""
    data = {
        "age": 30,
        "spending": {
            "yearly_amount": 60,
        },
    }
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**data)
