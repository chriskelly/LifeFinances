"""ConfTest Module"""
# pylint:disable=redefined-outer-name

import yaml
import pytest
from app import create_app
from app.data import constants
from app.models.config import User
from app.models.financial.state import gen_first_state


@pytest.fixture
def app():
    """Flask App"""
    app = create_app()
    return app


@pytest.fixture
def sample_config_data():
    """Pull in current user's config"""
    with open(constants.SAMPLE_FULL_CONFIG_PATH, "r", encoding="utf-8") as file:
        sample_data = yaml.safe_load(file)
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
def min_users():
    """Returns User objects based on the two minimum config

    Returns:
        tuple[User]: (User based on min income config, User based on min net worth config)
    """
    with open(constants.SAMPLE_MIN_CONFIG_INCOME_PATH, "r", encoding="utf-8") as file:
        min_income_data = yaml.safe_load(file)
    with open(
        constants.SAMPLE_MIN_CONFIG_NET_WORTH_PATH, "r", encoding="utf-8"
    ) as file:
        min_net_worth_data = yaml.safe_load(file)
    return (User(**min_income_data), User(**min_net_worth_data))
