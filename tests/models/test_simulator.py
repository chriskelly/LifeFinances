"""Testing for models/simulator.py"""
# pylint:disable=missing-class-docstring


import pytest
from app.models.simulator import (
    SimulationEngine,
)


class TestSimulationEngine:
    def test_gen_all_trials(self):
        """Ensure simulation runs without error"""
        engine = SimulationEngine()
        try:
            engine.gen_all_trials()
        except Exception as exception:  # pylint:disable=broad-exception-caught # NA
            pytest.fail(f"Function raised an exception: {exception}")

    def test_gen_all_trails_min_config(self, monkeypatch, min_user):
        """Ensure simulation runs without error with minimum config"""

        def mock_get_min_config_impl():
            return min_user

        monkeypatch.setattr("app.models.simulator.get_config", mock_get_min_config_impl)

        self.test_gen_all_trials()
