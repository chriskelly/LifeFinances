"""Testing for models/simulator.py"""
# pylint:disable=missing-class-docstring


from pathlib import Path
import pytest
from pytest_mock import MockerFixture
from app.data import constants
from app.models.simulator import (
    Results,
    SimulationEngine,
    ResultLabels,
    SimulationTrial,
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


def _gen_results():
    engine = SimulationEngine(
        trial_qty=1, config_path=constants.SAMPLE_FULL_CONFIG_PATH
    )
    engine.gen_all_trials()
    return engine.results.as_dataframes()


class TestResults:
    results = _gen_results()[0]

    def test_incomes(self):
        """All incomes should be positive or 0"""
        assert (self.results[ResultLabels.JOB_INCOME.value] >= 0).all()
        assert (self.results[ResultLabels.SS_USER.value] >= 0).all()
        assert (self.results[ResultLabels.SS_PARTNER.value] >= 0).all()
        assert (self.results[ResultLabels.PENSION.value] >= 0).all()
        assert (self.results[ResultLabels.TOTAL_INCOME.value] >= 0).all()

    def test_costs(self):
        """These costs should be negative or 0"""
        assert (self.results[ResultLabels.SPENDING.value] <= 0).all()
        assert (self.results[ResultLabels.KIDS.value] <= 0).all()
        assert (self.results[ResultLabels.INCOME_TAXES.value] <= 0).all()
        assert (self.results[ResultLabels.MEDICARE_TAXES.value] <= 0).all()
        assert (self.results[ResultLabels.SOCIAL_SECURITY_TAXES.value] <= 0).all()

    def test_calc_success_rate(self, mocker: MockerFixture):
        """calc_success_rate should return the correct value"""
        successful_trial_mock = mocker.MagicMock(spec=SimulationTrial)
        successful_trial_mock.get_success.return_value = True
        failed_trial_mock = mocker.MagicMock(spec=SimulationTrial)
        failed_trial_mock.get_success.return_value = False
        results = Results(
            trials=[
                successful_trial_mock,
                successful_trial_mock,
                successful_trial_mock,
                failed_trial_mock,
                failed_trial_mock,
            ]
        )
        assert results.calc_success_rate() == pytest.approx(0.6)
        assert results.calc_success_percentage() == "60.0"
