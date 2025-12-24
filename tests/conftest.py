"""ConfTest Module"""

from typing import Any, cast

import pytest
import yaml

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
