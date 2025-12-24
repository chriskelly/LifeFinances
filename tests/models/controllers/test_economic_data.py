"""Testing for models/controllers/economic_data.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

from pathlib import Path

import numpy as np
import pytest

from app.models.controllers.economic_data import (
    CsvVariableMixRepo,
    EconomicEngine,
    VariableMix,
    VariableMixRepo,
    _gen_variable_data,
)
from tests.conftest import AssetStats


@pytest.fixture
def csv_variable_mix_repo(test_statistics_csv_path: Path):
    """Returns a VariableMixRepo"""
    return CsvVariableMixRepo(statistics_path=test_statistics_csv_path)


def test_csv_variable_mix_repo(
    csv_variable_mix_repo: CsvVariableMixRepo, assets: AssetStats
):
    """Should read from csv and return a VariableMix"""
    variable_mix = csv_variable_mix_repo.get_variable_mix()
    assert isinstance(variable_mix, VariableMix)
    assert len(variable_mix.variable_stats) == 5
    assert variable_mix.variable_stats[0].mean_yield == pytest.approx(
        assets.us_stock.expected_yield
    )
    assert variable_mix.variable_stats[0].stdev == pytest.approx(assets.us_stock.stdev)
    assert variable_mix.variable_stats[1].mean_yield == pytest.approx(
        assets.us_bond.expected_yield
    )
    assert variable_mix.variable_stats[1].stdev == pytest.approx(assets.us_bond.stdev)
    assert variable_mix.variable_stats[2].mean_yield == pytest.approx(
        assets.tips.expected_yield
    )
    assert variable_mix.variable_stats[2].stdev == pytest.approx(assets.tips.stdev)
    assert variable_mix.variable_stats[3].mean_yield == pytest.approx(
        assets.intl_ex_us_stock.expected_yield
    )
    assert variable_mix.variable_stats[3].stdev == pytest.approx(
        assets.intl_ex_us_stock.stdev
    )
    assert variable_mix.variable_stats[4].mean_yield == pytest.approx(1.03)  # Inflation
    assert variable_mix.variable_stats[4].stdev == pytest.approx(0.02)


class TestGenerateRates:
    trial_qty = 10
    intervals_per_trial = 1000
    variable_mix = None
    yields = None

    @pytest.fixture(autouse=True)
    def class_attributes_fixture(self, csv_variable_mix_repo: CsvVariableMixRepo):
        """Generate a variable mix and the covariated data for the tests in this class"""
        self.variable_mix = csv_variable_mix_repo.get_variable_mix()
        self.yields = _gen_variable_data(
            variable_mix=self.variable_mix,
            trial_qty=self.trial_qty,
            intervals_per_trial=self.intervals_per_trial,
            seeded=True,
        )

    def test_shape(self):
        """Rates should have the correct shape"""
        assert self.yields.shape == (
            self.trial_qty,
            self.intervals_per_trial,
            len(self.variable_mix.variable_stats),
        )

    def test_statistics(self):
        """Rates should have the correct mean and standard deviation"""
        for trial_yields in self.yields:
            for asset_idx, asset_yields in enumerate(trial_yields.T):
                interval_behavior = self.variable_mix.variable_stats[
                    asset_idx
                ].gen_interval_behavior()
                assert np.mean(asset_yields) == pytest.approx(
                    interval_behavior.mean_yield, rel=0.01
                )
                assert np.std(asset_yields) == pytest.approx(
                    interval_behavior.stdev, rel=0.1
                )


class TestEconomicEngine:
    trial_qty = 2
    intervals_per_trial = 4
    economic_engine = None

    @pytest.fixture(autouse=True)
    def gen_economic_engine(self, csv_variable_mix_repo: VariableMixRepo):
        """Generate an EconomicEngine"""
        self.economic_engine = EconomicEngine(
            intervals_per_trial=self.intervals_per_trial,
            trial_qty=self.trial_qty,
            variable_mix_repo=csv_variable_mix_repo,
        )

    def test_split_inflation_from_assets(self, assets: AssetStats):
        """Inflation and asset data should be split correctly"""
        assert self.economic_engine._inflation_data.shape == (
            self.trial_qty,
            self.intervals_per_trial,
        )
        assert self.economic_engine._asset_data.shape == (
            self.trial_qty,
            self.intervals_per_trial,
            len(self.economic_engine._variable_mix.variable_stats) - 1,
        )
        assert self.economic_engine._lookup_table == {
            assets.us_stock.label: 0,
            assets.us_bond.label: 1,
            assets.tips.label: 2,
            assets.intl_ex_us_stock.label: 3,
        }

    def test_make_inflation_cumulative(self):
        """Inflation data should be a cumulative buildup. Each next value should be
        the previous value times the next inflation yield."""
        self.economic_engine._inflation_data = np.array(
            [
                [1, 0.9, 1.2, 1.1],
                [1.3, 0.8, 1.1, 1],
            ]
        )
        self.economic_engine._make_inflation_cumulative()
        assert self.economic_engine._inflation_data[0][0] == pytest.approx(1)
        assert self.economic_engine._inflation_data[0][1] == pytest.approx(0.9)
        assert self.economic_engine._inflation_data[0][2] == pytest.approx(1.08)
        assert self.economic_engine._inflation_data[0][3] == pytest.approx(1.188)
        assert self.economic_engine._inflation_data[1][0] == pytest.approx(1.3)
        assert self.economic_engine._inflation_data[1][1] == pytest.approx(1.04)
        assert self.economic_engine._inflation_data[1][2] == pytest.approx(1.144)
        assert self.economic_engine._inflation_data[1][3] == pytest.approx(1.144)
