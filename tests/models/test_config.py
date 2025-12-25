"""Testing for models/config.py
run `python3 -m pytest` if VSCode Testing won't load
"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

from dataclasses import dataclass
from typing import Any, cast

import pytest
import yaml
from pydantic import ValidationError
from pytest_mock.plugin import MockerFixture

from app.data import constants
from app.models.config import (
    IncomeProfile,
    SpendingProfile,
    StrategyConfig,
    StrategyOptions,
    User,
    _income_profiles_in_order,
    _spending_profiles_validation,
    attribute_filler,
    write_config_file,
)


def test_sample_config_data(sample_config_data):
    """Ensure sample data is valid"""
    assert sample_config_data
    try:
        user = User(**sample_config_data)
        # If the config model is changed, but the sample_config isn't updated
        # correctly, this test should help capture undeclared objects
        exceptions = {"same", "net_worth_target"}

        def check_for_none(obj, parent_path=""):
            for key, value in obj.items():
                if value is None and key not in exceptions:
                    pytest.fail(f"Value at path '{parent_path}.{key}' is None")
                elif isinstance(value, dict):
                    check_for_none(value, parent_path=f"{parent_path}.{key}")

        check_for_none(user.model_dump())
    except ValidationError as error:
        pytest.fail(f"Failed to validate sample user data: {error}")


def test_user_data():
    """Ensure user's data is valid"""
    with open(constants.CONFIG_PATH, encoding="utf-8") as file:
        user_data = cast(dict[str, Any], yaml.safe_load(file))
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
        with open(path, encoding="utf-8") as file:
            user_data = cast(dict[str, Any], yaml.safe_load(file))
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
        str1: str | None = None
        str2: str | None = None

    @dataclass
    class SecondLevelObj:
        third_lvl: ThirdLevelObj
        str1: str | None = None

    @dataclass
    class FirstLevelObj:
        second_lvl: SecondLevelObj
        str1: str | None = None

    # Test that it won't fill set values
    obj = FirstLevelObj(
        str1="World",
        second_lvl=SecondLevelObj(
            str1="World", third_lvl=ThirdLevelObj(str1="World", str2="World")
        ),
    )
    attribute_filler(obj=obj, attr="str1", fill_value="Hello")
    assert obj.str1 == "World"
    assert obj.second_lvl.third_lvl.str1 == "World"
    assert obj.second_lvl.third_lvl.str2 == "World"

    # Test that it will fill unspecified values
    obj = FirstLevelObj(second_lvl=SecondLevelObj(third_lvl=ThirdLevelObj()))
    attribute_filler(obj=obj, attr="str1", fill_value="Hello")
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
            "profiles": [{"yearly_amount": 10000}],
        },
    }
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**data)


def test_write_config_file(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch):
    """Ensure write_config_file works as expected and fails when necessary"""
    with open(constants.SAMPLE_MIN_CONFIG_NET_WORTH_PATH, encoding="utf-8") as file:
        min_config = file.read()

    mock_open = mocker.MagicMock()
    monkeypatch.setattr("builtins.open", mock_open)

    # Test valid YAML
    write_config_file(min_config)
    mock_open.assert_called_once()

    # Test invalid YAML loading
    config_text = min_config.replace(":", "")
    with pytest.raises(TypeError):
        write_config_file(config_text)

    # Test invalid YAML format
    invalid_yaml = """
    key: value
    - item1
    - item2
    """
    with pytest.raises(yaml.YAMLError):
        write_config_file(invalid_yaml)

    # Test invalid config
    config_text = min_config.replace("age", "wrong_key")
    with pytest.raises(ValidationError):
        write_config_file(config_text)


def test_total_portfolio_strategy_config_loading(sample_config_data):
    """Test that total_portfolio strategy can be loaded from YAML config"""
    from app.models.config import TotalPortfolioStrategyConfig

    # Modify sample config to choose total_portfolio instead of flat
    sample_config_data["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False
    sample_config_data["portfolio"]["allocation_strategy"]["total_portfolio"][
        "chosen"
    ] = True

    user = User(**sample_config_data)
    assert user.portfolio.allocation_strategy.total_portfolio is not None
    assert isinstance(
        user.portfolio.allocation_strategy.total_portfolio, TotalPortfolioStrategyConfig
    )
    assert user.portfolio.allocation_strategy.total_portfolio.enabled is True
    assert user.portfolio.allocation_strategy.total_portfolio.chosen is True
    assert user.portfolio.allocation_strategy.total_portfolio.low_risk_allocation == {
        "TIPS": 0.8,
        "US_Bond": 0.2,
    }
    assert user.portfolio.allocation_strategy.total_portfolio.high_risk_allocation == {
        "US_Stock": 0.7,
        "Intl_ex_US_Stock": 0.3,
    }
    assert user.portfolio.allocation_strategy.total_portfolio.RRA == 2.5

    # Verify chosen_strategy recognizes total_portfolio
    strategy_name, strategy_obj = user.portfolio.allocation_strategy.chosen_strategy
    assert strategy_name == "total_portfolio"
    assert isinstance(strategy_obj, TotalPortfolioStrategyConfig)


def test_total_portfolio_strategy_requires_age_based_social_security(
    sample_config_data,
):
    """Total portfolio strategy requires age-based social security strategy"""
    # Modify sample config to use total_portfolio and net_worth-based social security
    config = sample_config_data.copy()
    config["portfolio"]["allocation_strategy"]["total_portfolio"]["chosen"] = True
    config["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False
    config["social_security_pension"]["strategy"]["net_worth"]["chosen"] = True
    config["social_security_pension"]["strategy"]["mid"]["chosen"] = False

    with pytest.raises(ValidationError) as exc_info:
        User(**config)

    assert "total_portfolio allocation strategy" in str(exc_info.value).lower()
    assert "social security" in str(exc_info.value).lower()
    assert "age-based" in str(exc_info.value).lower()


def test_total_portfolio_strategy_requires_age_based_or_cashout_pension(
    sample_config_data,
):
    """Total portfolio strategy requires age-based or cashout pension strategy"""
    # Modify sample config to use total_portfolio and add admin with net_worth-based pension
    config = sample_config_data.copy()
    config["portfolio"]["allocation_strategy"]["total_portfolio"]["chosen"] = True
    config["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False
    config["admin"] = {
        "pension": {
            "trust_factor": 1.0,
            "account_balance": 100,
            "balance_update": 2022.5,
            "strategy": {
                "mid": {"enabled": False, "chosen": False},
                "net_worth": {
                    "enabled": True,
                    "chosen": True,
                    "net_worth_target": 1000,
                },
            },
        }
    }

    with pytest.raises(ValidationError) as exc_info:
        User(**config)

    assert "total_portfolio allocation strategy" in str(exc_info.value).lower()
    assert "pension" in str(exc_info.value).lower()


def test_total_portfolio_strategy_allows_age_based_strategies(sample_config_data):
    """Total portfolio strategy works with age-based benefit strategies"""
    # Modify sample config to use total_portfolio with age-based strategies
    config = sample_config_data.copy()
    config["portfolio"]["allocation_strategy"]["total_portfolio"]["chosen"] = True
    config["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False
    # Social security already uses 'mid' (age-based) in sample config

    # Should not raise
    user = User(**config)
    assert user.portfolio.allocation_strategy.chosen_strategy[0] == "total_portfolio"
    assert user.social_security_pension.strategy.chosen_strategy[0] == "mid"


def test_total_portfolio_strategy_allows_cashout_pension(sample_config_data):
    """Total portfolio strategy works with cashout pension strategy"""
    # Modify sample config to use total_portfolio and add admin with cashout pension
    config = sample_config_data.copy()
    config["portfolio"]["allocation_strategy"]["total_portfolio"]["chosen"] = True
    config["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False
    config["admin"] = {
        "pension": {
            "trust_factor": 1.0,
            "account_balance": 100,
            "balance_update": 2022.5,
            "strategy": {
                "mid": {"enabled": False, "chosen": False},
                "cash_out": {"enabled": True, "chosen": True},
            },
        }
    }

    # Should not raise
    user = User(**config)
    assert user.portfolio.allocation_strategy.chosen_strategy[0] == "total_portfolio"
    assert user.admin.pension.strategy.chosen_strategy[0] == "cash_out"
