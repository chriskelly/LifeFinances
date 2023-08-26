"""Testing for models/simulator.py"""
# pylint:disable=missing-class-docstring


import pytest
from app.models.simulator import (
    SimulationEngine,
)


class TestSimulationEngine:
    def test_gen_all_trials(self):
        """Ensure simulation runs without error"""
        engine = SimulationEngine(trial_qty=5)  # speed up tests
        try:
            engine.gen_all_trials()
        except Exception as exception:  # pylint:disable=broad-exception-caught # NA
            pytest.fail(f"Function raised an exception: {exception}")

    def test_gen_all_trails_sample_configs(self, monkeypatch, min_users, sample_user):
        """Ensure simulation runs without error for sample configs"""
        min_user_income, min_user_net_worth = min_users

        # Test min config that includes income
        def mock_get_user_min_income():
            return min_user_income

        monkeypatch.setattr("app.models.simulator.get_config", mock_get_user_min_income)
        self.test_gen_all_trials()

        # Test min config that includes net worth
        def mock_get_user_min_net_worth():
            return min_user_net_worth

        monkeypatch.setattr(
            "app.models.simulator.get_config", mock_get_user_min_net_worth
        )
        self.test_gen_all_trials()

        # Test sample full config
        def mock_get_user_sample():
            return sample_user

        monkeypatch.setattr("app.models.simulator.get_config", mock_get_user_sample)
        self.test_gen_all_trials()
