"""Testing for models/financials/allocation.py
"""
# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name

import numpy as np
import pytest
from app.models.controllers.allocation import (
    _FlatAllocationStrategy,
    _NetWorthPivotStrategy,
)
from app.models.config import NetWorthPivotStrategyConfig, User
from app.models.financial.state import State


def test_flat_allocation_strategy(sample_user: User, first_state):
    """Should return an np.ndarray with the correct ratios"""
    asset_lookup = {
        "US_Stock": 0,
        "US_Bond": 1,
    }
    sample_config = sample_user.portfolio.allocation_strategy.flat
    strategy = _FlatAllocationStrategy(config=sample_config, asset_lookup=asset_lookup)
    allocation = strategy.gen_allocation(first_state)
    assert isinstance(allocation, np.ndarray)
    assert allocation == pytest.approx([0.6, 0.4])


def test_net_worth_pivot_strategy(first_state: State):
    """Test that the net worth pivot strategy returns the correct ratios

    The strategy should return the under target allocation if the net worth is
    below the target, and a weighted average of the under and over target
    allocations if the net worth is above the target. Target should be adjusted
    for inflation.
    """
    asset_lookup = {
        "US_Stock": 0,
        "US_Bond": 1,
        "10_yr_Treasury": 2,
        "TIPS": 3,
    }
    under_target_allocation = np.array([0.8, 0.2, 0, 0])
    under_target_allocation_config = dict(
        zip(asset_lookup.keys(), under_target_allocation)
    )
    over_target_allocation = np.array([0.2, 0, 0.4, 0.4])
    over_target_allocation_config = dict(
        zip(asset_lookup.keys(), over_target_allocation)
    )
    net_worth_target = 100
    strategy = _NetWorthPivotStrategy(
        config=NetWorthPivotStrategyConfig(
            under_target_allocation=under_target_allocation_config,
            over_target_allocation=over_target_allocation_config,
            net_worth_target=net_worth_target,
        ),
        asset_lookup=asset_lookup,
    )

    first_state.net_worth = net_worth_target * 0.9  # Under target
    assert strategy.gen_allocation(first_state) == pytest.approx(
        under_target_allocation
    )

    first_state.net_worth = net_worth_target  # At target
    assert strategy.gen_allocation(first_state) == pytest.approx(
        under_target_allocation
    )

    first_state.net_worth = net_worth_target * 4  # Over target
    expected_allocation = (0.25 * under_target_allocation) + (
        0.75 * over_target_allocation
    )
    assert strategy.gen_allocation(first_state) == pytest.approx(expected_allocation)

    first_state.net_worth = net_worth_target * 5
    first_state.inflation = 4  # Over target, with inflation
    expected_allocation = (0.8 * under_target_allocation) + (
        0.2 * over_target_allocation
    )
    assert strategy.gen_allocation(first_state) == pytest.approx(expected_allocation)
