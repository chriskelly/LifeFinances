import pytest
from pytest_mock.plugin import MockerFixture
from app.models.controllers import Controllers
from app.models.financial.state_change import StateChangeComponents


@pytest.fixture
def controllers_mock(mocker: MockerFixture):
    """Fixture for an empty Controllers"""
    return mocker.MagicMock(spec=Controllers)


@pytest.fixture
def components_mock(mocker: MockerFixture):
    """Fixture for an empty StateChangeComponents"""
    return mocker.MagicMock(spec=StateChangeComponents)
