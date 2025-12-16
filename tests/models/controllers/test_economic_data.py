"""Testing for models/controllers/economic_data.py"""

# pylint:disable=redefined-outer-name,missing-class-docstring,protected-access
# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import csv
from pathlib import Path
import pytest
import numpy as np
from app.models.controllers.economic_data import (
    CsvVariableMixRepo,
    EconomicEngine,
    VariableMix,
    VariableMixRepo,
    _gen_covariated_data,
)


@pytest.fixture
def csv_variable_mix_repo():
    """Returns a VariableMixRepo"""
    statistics_path = Path(
        "tests/models/controllers/test_csv_variable_mix_repo_statistics.csv"
    )
    correlation_path = Path(
        "tests/models/controllers/test_csv_variable_mix_repo_correlation.csv"
    )
    return CsvVariableMixRepo(
        statistics_path=statistics_path, correlation_path=correlation_path
    )


def test_csv_variable_mix_repo(csv_variable_mix_repo: CsvVariableMixRepo):
    """Should read from csv and return a VariableMix"""
    variable_mix = csv_variable_mix_repo.get_variable_mix()
    assert isinstance(variable_mix, VariableMix)
    assert len(variable_mix.variable_stats) == 3
    assert variable_mix.correlation_matrix.shape == (3, 3)
    assert variable_mix.correlation_matrix[0, 0] == pytest.approx(1.0)
    assert variable_mix.correlation_matrix[0, 1] == pytest.approx(0.5)
    assert variable_mix.correlation_matrix[0, 2] == pytest.approx(0.4)
    assert variable_mix.correlation_matrix[1, 0] == pytest.approx(0.5)
    assert variable_mix.correlation_matrix[1, 1] == pytest.approx(1.0)
    assert variable_mix.correlation_matrix[1, 2] == pytest.approx(-0.7)
    assert variable_mix.correlation_matrix[2, 0] == pytest.approx(0.4)
    assert variable_mix.correlation_matrix[2, 1] == pytest.approx(-0.7)
    assert variable_mix.correlation_matrix[2, 2] == pytest.approx(1.0)
    assert variable_mix.variable_stats[0].mean_yield == pytest.approx(1.08)
    assert variable_mix.variable_stats[0].stdev == pytest.approx(0.15)
    assert variable_mix.variable_stats[1].mean_yield == pytest.approx(1.1)
    assert variable_mix.variable_stats[1].stdev == pytest.approx(0.2)
    assert variable_mix.variable_stats[2].mean_yield == pytest.approx(1.12)
    assert variable_mix.variable_stats[2].stdev == pytest.approx(0.18)


class TestGenerateRates:
    trial_qty = 10
    intervals_per_trial = 1000
    variable_mix = None
    yields = None

    @pytest.fixture(autouse=True)
    def class_attributes_fixture(self, csv_variable_mix_repo: CsvVariableMixRepo):
        """Generate a variable mix and the covariated data for the tests in this class"""
        self.variable_mix = csv_variable_mix_repo.get_variable_mix()
        self.yields = _gen_covariated_data(
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

    def test_correlations(self):
        """Assets should have the correct correlations"""
        for i in range(len(self.variable_mix.variable_stats)):
            for j in range(i + 1, len(self.variable_mix.variable_stats)):
                asset1_returns = self.yields[:, :, i]
                asset2_returns = self.yields[:, :, j]
                calculated_correlation = np.corrcoef(
                    asset1_returns.flatten(), asset2_returns.flatten()
                )[0, 1]
                expected_correlation = self.variable_mix.correlation_matrix[i, j]

                assert (
                    pytest.approx(expected_correlation, rel=0.2)
                    == calculated_correlation
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

    def test_split_inflation_from_assets(self):
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
        assert self.economic_engine._lookup_table == {"US_Stock": 0, "US_Bond": 1}

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


def test_all_variables_have_correlation_data():
    """All variables in the statistics should have correlation data"""
    statistics_path = Path("app/data/variable_statistics.csv")
    correlation_path = Path("app/data/variable_correlation.csv")
    with open(statistics_path, "r", encoding="utf-8") as file:
        csv_reader = csv.reader(file, skipinitialspace=True)
        next(csv_reader)
        label_idx = 0
        variables = [csv_row[label_idx] for csv_row in csv_reader]
    combinations = set()
    for variable1 in variables:
        for variable2 in variables:
            if variable1 != variable2:
                combinations.add(tuple(sorted([variable1, variable2])))
    with open(correlation_path, "r", encoding="utf-8") as file:
        csv_reader = csv.reader(file, skipinitialspace=True)
        next(csv_reader)
        variable_1_idx = 0
        variable_2_idx = 1
        for csv_row in csv_reader:
            variable1 = csv_row[variable_1_idx]
            variable2 = csv_row[variable_2_idx]
            if variable1 != variable2:
                combinations.remove(tuple(sorted([variable1, variable2])))
    assert len(combinations) == 0
