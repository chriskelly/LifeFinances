"""Testing for models/financials/allocation.py
run `python3 -m pytest` if VSCode Testing won't load
"""
# pylint:disable=missing-class-docstring

from copy import copy
import pytest
from app.models import config
from app.models.financial.state import State
from app.models.financial.allocation import (
    FlatBondStrategy,
    XMinusAgeStrategy,
    BondTentStrategy,
    RiskRatios,
    LifeCycleStrategy,
    Controller,
)
from app.models.config import User, AllocationOptions


def test_risk_ratios_post_init():
    """If only one argument is passed to RiskRatios,
    the other value should be filled in by the __post_init__
    method. The two ratios should add to one"""
    ratios = RiskRatios(low=0.2)
    assert ratios.low + ratios.high == 1

    ratios = RiskRatios(high=0.2)
    assert ratios.low + ratios.high == 1


def test_flat_bond_strategy(sample_user: User, first_state):
    """Low risk ratio should be equal to flat_bond_target"""
    sample_config = sample_user.portfolio.allocation_strategy.flat_bond
    strategy = FlatBondStrategy(config=sample_config)
    risk_ratio = strategy.risk_ratio(first_state)
    assert risk_ratio.low == sample_config.flat_bond_target


class TestXMinusAge:
    strategy = XMinusAgeStrategy(config=config.XMinusAgeStrategyConfig(x=100))

    def test_risk_ratio_with_partner(self, first_state: State):
        """This strategy should use the average age between partners"""
        assert first_state.user.partner
        first_state.user.age = 20
        first_state.user.partner.age = 30
        risk_ratio = self.strategy.risk_ratio(first_state)
        assert risk_ratio.low == pytest.approx(0.25)
        assert risk_ratio.high == pytest.approx(0.75)

    def test_risk_ratio_without_partner(self, first_state: State):
        """If there is no partner, should just use the user's age"""
        first_state.user.partner = None
        first_state.user.age = 20
        risk_ratio = self.strategy.risk_ratio(first_state)
        assert risk_ratio.low == pytest.approx(0.20)
        assert risk_ratio.high == pytest.approx(0.80)


def test_bond_tent_strategy(first_state: State):
    """Low risk should match path defined in the config_obj"""
    config_obj = config.BondTentStrategyConfig(
        start_allocation=0.3,
        start_date=1,
        peak_allocation=0.7,
        peak_date=3,
        end_allocation=0.1,
        end_date=6,
    )
    strategy = BondTentStrategy(config=config_obj)
    # Create states with incrementally increasing dates
    states = []
    for i in range(8):
        state = copy(first_state)
        state.date = i
        states.append(state)
    # Find the low risk ratio for each state
    low_risk = [strategy.risk_ratio(states[i]).low for i in range(8)]
    # Experimentally derived correct answers
    expected_results = [0.3, 0.3, 0.5, 0.7, 0.5, 0.3, 0.1, 0.1]
    for i in range(8):
        assert low_risk[i] == pytest.approx(expected_results[i])


class TestLifeCycle:
    strategy = LifeCycleStrategy(
        config=config.LifeCycleStrategyConfig(equity_target=1000)
    )

    def test_constraint(self, first_state: State):
        """Risk ratio should not be outside the bounds of 0 - 1"""
        first_state.net_worth = 500
        risk_ratio = self.strategy.risk_ratio(first_state)
        assert risk_ratio.high == pytest.approx(1)
        first_state.net_worth = -200
        risk_ratio = self.strategy.risk_ratio(first_state)
        assert risk_ratio.high == pytest.approx(0)

    def test_risk_ratio(self, first_state: State):
        """High risk ratio should be `equity_target/net_worth`"""
        first_state.net_worth = 2000
        risk_ratio = self.strategy.risk_ratio(first_state)
        assert risk_ratio.high == pytest.approx(0.5)

    def test_inflation_adjustment(self, first_state: State):
        """Inflation over 1 should inflate the equity_target,
        increasing the high risk ratio"""
        first_state.net_worth = 2000
        first_state.inflation = 1.5
        risk_ratio = self.strategy.risk_ratio(first_state)
        assert risk_ratio.high == pytest.approx(0.75)


class TestGenAllocation:
    def test_bond_annuity_relationship(self, sample_user: User, first_state: State):
        """If annuities_instead_of_bonds is False, annuity allocation should be 0.
        If annuities_instead_of_bonds is True, bond allocation should be 0."""
        allocation_options = {
            "flat_bond": {
                "chosen": True,
                "flat_bond_target": 0.5,
            }
        }
        sample_user.portfolio.allocation_strategy = AllocationOptions(
            **allocation_options
        )
        sample_user.portfolio.annuities_instead_of_bonds = False
        allocation = Controller(sample_user).gen_allocation(first_state)
        assert allocation.bond == pytest.approx(0.5)
        assert allocation.annuity == pytest.approx(0)
        sample_user.portfolio.annuities_instead_of_bonds = True
        allocation = Controller(sample_user).gen_allocation(first_state)
        assert allocation.bond == pytest.approx(0)
        assert allocation.annuity == pytest.approx(0.5)

    def test_stock_real_estate_relationship(
        self, sample_user: User, first_state: State
    ):
        """Real estate and stock allocation should be complimentary"""
        sample_user.portfolio.real_estate.include.equity_ratio = 0.25
        allocation = Controller(sample_user).gen_allocation(first_state)
        low_risk_ratio = allocation.bond + allocation.annuity
        assert allocation.real_estate + allocation.stock == pytest.approx(
            1 - low_risk_ratio
        )
