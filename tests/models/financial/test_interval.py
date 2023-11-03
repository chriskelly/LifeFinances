"""Testing for models/financial/interval.py
"""
# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name

import pytest
from pytest_mock.plugin import MockerFixture
from app.data.constants import YEARS_PER_INTERVAL
from app.models.controllers import Controllers
from app.models.controllers.economic_data import EconomicStateData
from app.models.financial.interval import Interval
from app.models.financial.state_change import StateChangeComponents


def test_gen_next_interval(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    controllers_mock: Controllers,
    first_state,
    components_mock: StateChangeComponents,
):
    """Test that the next interval is generated correctly"""
    monkeypatch.setattr(
        "app.models.financial.state_change.StateChangeComponents.__init__",
        lambda *_: None,
    )
    interval = Interval(state=first_state, controllers=controllers_mock)
    interval.state_change_components = components_mock
    net_transactions_mock = 100
    interval.state_change_components.net_transactions = mocker.MagicMock()
    interval.state_change_components.net_transactions.sum = net_transactions_mock
    economic_state_data_mock = mocker.MagicMock(spec=EconomicStateData)
    next_inflation = 2
    economic_state_data_mock.inflation = next_inflation
    controllers_mock.economic_data.get_economic_state_data = (
        lambda *_: economic_state_data_mock
    )

    next_interval = interval.gen_next_interval(controllers_mock)

    assert next_interval.state.date == pytest.approx(
        interval.state.date + YEARS_PER_INTERVAL
    )
    assert next_interval.state.interval_idx == interval.state.interval_idx + 1
    assert next_interval.state.net_worth == pytest.approx(
        interval.state.net_worth + net_transactions_mock
    )
    assert next_interval.state.inflation == next_inflation
