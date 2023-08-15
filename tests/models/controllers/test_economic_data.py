"""Testing for models/controllers/economic_data.py"""
# pylint:disable=redefined-outer-name,missing-class-docstring,protected-access

import math
import pytest
import numpy as np
from scipy import stats
from app.models.controllers.economic_data import (
    Generator,
    InvestmentBehavior,
    INFLATION_BEHAVIOR,
    STOCK_BEHAVIOR,
    BOND_BEHAVIOR,
    REAL_ESTATE_BEHAVIOR,
)


@pytest.fixture
def generator():
    """Sample economic data generator"""
    return Generator(
        intervals_per_trial=350,
        intervals_per_year=4,
        trial_qty=10,
    )


class TestInflation:
    def test_create_skew_dist(self, generator: Generator):
        """Distribution characteristics should match input"""
        interval_behavior = INFLATION_BEHAVIOR.gen_interval_behavior(
            generator.intervals_per_year
        )
        size = generator.intervals_per_trial * generator.trial_qty
        distribution = generator._create_skew_dist(
            interval_behavior.mean_yield,
            interval_behavior.stdev,
            interval_behavior.skew,
            size,
        )
        assert interval_behavior.mean_yield == pytest.approx(
            np.mean(distribution), rel=0.01
        )
        assert interval_behavior.stdev == pytest.approx(np.std(distribution), rel=0.2)
        assert interval_behavior.skew == pytest.approx(
            stats.skew(distribution), rel=0.4
        )
        assert size == len(distribution)

    def test_generate_2d_inflation(self, generator: Generator):
        """Should generate a 2d list of inflation values"""
        inflation_matrix = generator._generate_2d_inflation()
        assert len(inflation_matrix) == generator.trial_qty
        assert len(inflation_matrix[0]) == generator.intervals_per_trial


class TestInvestmentReturns:
    investment_behavior = InvestmentBehavior(
        mean_yield=1.05,
        stdev=0.05,
        annualized_high=1.07,
        annualized_low=1.03,
    )

    def test_generate_1d_restricted_rates(self, generator: Generator):
        """Output statistics should match input"""
        interval_behavior = self.investment_behavior.gen_interval_behavior(
            generator.intervals_per_year
        )
        rates = generator._generate_1d_restricted_rates(interval_behavior)[0]
        yields = rates + 1
        assert np.mean(yields) == pytest.approx(interval_behavior.mean_yield, rel=0.01)
        assert np.std(yields) == pytest.approx(interval_behavior.stdev, rel=0.1)
        year_qty = math.ceil(
            generator.intervals_per_trial / generator.intervals_per_year
        )
        annualized_return = pow(np.prod(yields), 1 / year_qty)
        assert (
            self.investment_behavior.annualized_low
            <= annualized_return
            <= self.investment_behavior.annualized_high
        )

    def test_generate_2d_rates(self, generator: Generator):
        """Should generate a 2d list of investment values"""
        rate_matrix = generator._generate_2d_rates(self.investment_behavior)
        assert len(rate_matrix) == generator.trial_qty
        assert len(rate_matrix[0]) == generator.intervals_per_trial

    def test_iter_cnt(self, generator: Generator):
        """Iteration count should be 'reasonable' (less than 3x trial_qty)"""
        for investment_behavior in [
            STOCK_BEHAVIOR,
            BOND_BEHAVIOR,
            REAL_ESTATE_BEHAVIOR,
        ]:
            interval_behavior = investment_behavior.gen_interval_behavior(
                generator.intervals_per_year
            )
            trials = 100
            iteration_cnt = sum(
                generator._generate_1d_restricted_rates(interval_behavior)[1]
                for _ in range(trials)
            )
            assert iteration_cnt < trials * 3
