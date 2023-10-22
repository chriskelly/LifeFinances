"""Testing for models/financials/allocation.py
"""
# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name

import numpy as np
import pytest
from app.models.controllers.allocation import _FlatAllocationStrategy
from app.models.config import User


@pytest.fixture
def asset_lookup():
    """Lookup table for asset names to index in asset_rates array"""
    return {
        "US_Stock": 0,
        "US_Bond": 1,
    }


def test_flat_allocation_strategy(sample_user: User, first_state, asset_lookup: dict):
    """Should return an np.ndarray with the correct ratios"""
    sample_config = sample_user.portfolio.allocation_strategy.flat
    strategy = _FlatAllocationStrategy(config=sample_config, asset_lookup=asset_lookup)
    allocation = strategy.gen_allocation(first_state)
    assert isinstance(allocation, np.ndarray)
    assert allocation == pytest.approx([0.6, 0.4])
