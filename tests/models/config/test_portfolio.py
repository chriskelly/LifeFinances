"""Testing for models/config/portfolio.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest
from pydantic import ValidationError

from app.models.config import TotalPortfolioStrategyConfig, User


def test_total_portfolio_strategy_config_defaults():
    """Test that TotalPortfolioStrategyConfig has correct defaults"""
    config = TotalPortfolioStrategyConfig()
    assert config.low_risk_allocation == {"TIPS": 1.0}
    assert config.high_risk_allocation == {"US_Stock": 1.0}
    assert config.RRA == 2.0
    assert config.enabled is False
    assert config.chosen is False


def test_total_portfolio_strategy_config_valid_allocation():
    """Test that valid allocations are accepted"""
    config = TotalPortfolioStrategyConfig(
        low_risk_allocation={"TIPS": 0.8, "US_Bond": 0.2},
        high_risk_allocation={"US_Stock": 0.7, "Intl_ex_US_Stock": 0.3},
        RRA=2.5,
    )
    assert config.low_risk_allocation == {"TIPS": 0.8, "US_Bond": 0.2}
    assert config.high_risk_allocation == {"US_Stock": 0.7, "Intl_ex_US_Stock": 0.3}
    assert config.RRA == 2.5


def test_total_portfolio_strategy_config_allocation_must_sum_to_1():
    """Test that allocations must sum to 1.0"""
    with pytest.raises(ValidationError) as exc_info:
        TotalPortfolioStrategyConfig(
            low_risk_allocation={"TIPS": 0.5},  # Sums to 0.5, not 1.0
            high_risk_allocation={"US_Stock": 1.0},
        )
    assert "must sum to 1" in str(exc_info.value).lower()

    with pytest.raises(ValidationError) as exc_info:
        TotalPortfolioStrategyConfig(
            low_risk_allocation={"TIPS": 1.0},
            high_risk_allocation={
                "US_Stock": 0.8,
                "Intl_ex_US_Stock": 0.3,
            },  # Sums to 1.1, not 1.0
        )
    assert "must sum to 1" in str(exc_info.value).lower()


def test_total_portfolio_strategy_config_invalid_asset():
    """Test that disallowed assets raise ValueError"""
    with pytest.raises(ValidationError) as exc_info:
        TotalPortfolioStrategyConfig(
            low_risk_allocation={"InvalidAsset": 1.0},
            high_risk_allocation={"US_Stock": 1.0},
        )
    assert "not allowed" in str(exc_info.value).lower()

    with pytest.raises(ValidationError) as exc_info:
        TotalPortfolioStrategyConfig(
            low_risk_allocation={"TIPS": 1.0},
            high_risk_allocation={"InvalidAsset": 1.0},
        )
    assert "not allowed" in str(exc_info.value).lower()


def test_total_portfolio_strategy_config_rra_must_be_positive():
    """Test that RRA must be greater than 0"""
    # Valid RRA values
    config1 = TotalPortfolioStrategyConfig(RRA=0.1)
    assert config1.RRA == 0.1

    config2 = TotalPortfolioStrategyConfig(RRA=10.0)
    assert config2.RRA == 10.0

    # Invalid: RRA = 0
    with pytest.raises(ValidationError) as exc_info:
        TotalPortfolioStrategyConfig(RRA=0)
    assert "RRA must be greater than 0" in str(exc_info.value)

    # Invalid: RRA < 0
    with pytest.raises(ValidationError) as exc_info:
        TotalPortfolioStrategyConfig(RRA=-1.0)
    assert "RRA must be greater than 0" in str(exc_info.value)


def test_total_portfolio_strategy_config_chosen_forces_enabled():
    """Test that chosen=True forces enabled=True"""
    config = TotalPortfolioStrategyConfig(chosen=True)
    assert config.enabled is True
    assert config.chosen is True


def test_total_portfolio_strategy_config_loading(sample_config_data):
    """Test that total_portfolio strategy can be loaded from YAML config"""
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
