"""Testing for models/config/strategy.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest

from app.models.config import StrategyConfig, StrategyOptions


def test_chosen_forces_enabled():
    """Any strategy with chosen=True should be enabled"""
    strategy = StrategyConfig(enabled=False, chosen=True)
    assert strategy.enabled is True


@pytest.fixture
def strategy_options() -> StrategyOptions:
    """Sample StrategyOptions"""

    class MyOptions(StrategyOptions):
        strategy1: StrategyConfig
        strategy2: StrategyConfig
        strategy3: StrategyConfig

    my_options = MyOptions(
        strategy1=StrategyConfig(enabled=True),
        strategy2=StrategyConfig(enabled=False),
        strategy3=StrategyConfig(enabled=True, chosen=True),
    )
    return my_options


def test_enabled_strategies(strategy_options: StrategyOptions):
    """All strategies with `enabled=True` in a StrategyOption instance
    should be included in the `enabled_strategies` property"""
    enabled_strategies = strategy_options.enabled_strategies
    assert enabled_strategies is not None
    assert len(enabled_strategies) == 2
    assert "strategy1" in enabled_strategies
    assert "strategy3" in enabled_strategies
    assert "strategy2" not in enabled_strategies


def test_chosen_strategy(strategy_options: StrategyOptions):
    """The strategy with `chosen=True` should
    be the `chosen_strategy` of a StrategyOption instance."""
    chosen_strategy = strategy_options.chosen_strategy
    assert chosen_strategy[0] == "strategy3"
