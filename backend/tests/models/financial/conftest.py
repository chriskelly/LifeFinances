import pytest
from pytest_mock.plugin import MockerFixture

from app.models.controllers import Controllers
from app.models.financial.state_change import StateChangeComponents


@pytest.fixture
def controllers_mock(mocker: MockerFixture):
    """Fixture for an empty Controllers"""
    mock = mocker.MagicMock(spec=Controllers)
    mock.allocation = mocker.MagicMock()
    mock.economic_data = mocker.MagicMock()
    mock.job_income = mocker.MagicMock()
    mock.social_security = mocker.MagicMock()
    mock.pension = mocker.MagicMock()
    mock.annuity = mocker.MagicMock()
    return mock


@pytest.fixture
def components_mock(mocker: MockerFixture):
    """Fixture for an empty StateChangeComponents"""
    return mocker.MagicMock(spec=StateChangeComponents)
