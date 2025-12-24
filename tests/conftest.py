"""ConfTest Module"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from app import create_app
from app.data import constants
from app.models.config import User
from app.models.controllers.economic_data import CsvVariableMixRepo
from app.models.financial.state import gen_first_state


@dataclass
class AssetStat:
    """Statistics for a single asset"""

    label: str
    expected_yield: float
    expected_return: float
    stdev: float


@dataclass
class AssetStats:
    """Container for all asset statistics"""

    tips: AssetStat
    us_stock: AssetStat
    us_bond: AssetStat
    intl_ex_us_stock: AssetStat


@pytest.fixture
def app():
    """Flask App"""
    app = create_app()
    return app


@pytest.fixture
def sample_config_data():
    """Pull in current user's config"""
    with open(constants.SAMPLE_FULL_CONFIG_PATH, encoding="utf-8") as file:
        sample_data = cast(dict[str, Any], yaml.safe_load(file))
    return sample_data


@pytest.fixture
def sample_user(sample_config_data):
    """Returns User object based on sample config"""
    return User(**sample_config_data)


@pytest.fixture
def first_state(sample_user: User):
    """Returns financial.state object for first state of sample user"""
    return gen_first_state(sample_user)


@pytest.fixture
def test_statistics_csv_path():
    """Returns path to the test CSV file with variable statistics"""
    return Path("tests/models/controllers/test_csv_variable_mix_repo_statistics.csv")


@pytest.fixture
def assets(test_statistics_csv_path: Path) -> AssetStats:
    """Extract asset statistics organized by asset type from test CSV"""
    repo = CsvVariableMixRepo(statistics_path=test_statistics_csv_path)
    variable_mix = repo.get_variable_mix()
    lookup = variable_mix.lookup_table

    def get_stat(label: str) -> AssetStat:
        """Helper to extract statistics for a given asset label"""
        idx = lookup[label]
        return AssetStat(
            label=label,
            expected_yield=variable_mix.variable_stats[idx].mean_yield,
            expected_return=variable_mix.variable_stats[idx].mean_yield - 1.0,
            stdev=variable_mix.variable_stats[idx].stdev,
        )

    return AssetStats(
        tips=get_stat(label="TIPS"),
        us_stock=get_stat(label="US_Stock"),
        us_bond=get_stat(label="US_Bond"),
        intl_ex_us_stock=get_stat(label="Intl_ex_US_Stock"),
    )
