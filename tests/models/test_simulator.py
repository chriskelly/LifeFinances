"""Testing for models/simulator.py"""
# pylint:disable=missing-class-docstring


from pathlib import Path
import pytest
from app.data import constants
from app.models.simulator import (
    SimulationEngine,
)


class TestSimulationEngine:
    def run_and_test_engine(self, config_path: Path):
        """Ensure simulation runs without error"""
        engine = SimulationEngine(trial_qty=5, config_path=config_path)
        try:
            engine.gen_all_trials()
        except Exception as exception:  # pylint:disable=broad-exception-caught # NA
            pytest.fail(f"Function raised an exception: {exception}")

    def test_user_config(self):
        """User config should run without error"""
        self.run_and_test_engine(constants.CONFIG_PATH)

    def test_min_income_config(self):
        """Min income config should run without error"""
        self.run_and_test_engine(constants.SAMPLE_MIN_CONFIG_INCOME_PATH)

    def test_min_net_worth_config(self):
        """Min net worth config should run without error"""
        self.run_and_test_engine(constants.SAMPLE_MIN_CONFIG_NET_WORTH_PATH)

    def test_sample_full_config(self):
        """Sample full config should run without error"""
        self.run_and_test_engine(constants.SAMPLE_FULL_CONFIG_PATH)
