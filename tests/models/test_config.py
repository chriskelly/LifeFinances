"""Testing for models/config.py
run `python3 -m pytest` if VSCode Testing won't load
"""
# pylint:disable=redefined-outer-name,missing-class-docstring

from typing import Optional
from dataclasses import dataclass
import yaml
import pytest
from pydantic import ValidationError
from app.data import constants
from app.models.config import (
    User,
    Strategy,
    StrategyOptions,
    attribute_filller,
)


@pytest.fixture
def sample_user_data():
    """Pull in current user's config"""
    with open(constants.CONFIG_PATH, "r", encoding="utf-8") as file:
        user_data = yaml.safe_load(file)
    return user_data


def test_sample_user_data(sample_user_data):
    """Ensure user data is valid"""
    assert sample_user_data
    try:
        User(**sample_user_data)
    except ValidationError as error:
        pytest.fail(f"Failed to validate sample user data: {error}")


def test_chosen_forces_enabled():
    """Any strategy with chosen=True should be enabled"""
    strategy = Strategy(enabled=False, chosen=True)
    assert strategy.enabled is True


@pytest.fixture
def strategy_options() -> StrategyOptions:
    """Sample StrategyOptions"""
    strategy1 = Strategy(enabled=True)
    strategy2 = Strategy(enabled=False)
    strategy3 = Strategy(enabled=True, chosen=True)

    @dataclass
    class MyOptions(StrategyOptions):
        strategy1: Strategy
        strategy2: Strategy
        strategy3: Strategy

    my_options = MyOptions(strategy1, strategy2, strategy3)
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


def test_user_state_supported(sample_user_data):
    """If the user selects a state not supported,
    a ValidationError should be captured."""
    sample_user_data["state"] = "Mexico"
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**sample_user_data)


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