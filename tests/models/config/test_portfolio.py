"""Testing for models/config/portfolio.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest
from pydantic import ValidationError

from app.models.config import TotalPortfolioStrategyConfig


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
