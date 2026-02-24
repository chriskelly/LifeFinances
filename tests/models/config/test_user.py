"""Testing for models/config/user.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

from typing import Any, cast

import pytest
import yaml
from pydantic import ValidationError

from app.data import constants
from app.models.config import User


def test_sample_config_data(sample_config_data):
    """Ensure sample data is valid"""
    assert sample_config_data
    try:
        user = User(**sample_config_data)
        # If the config model is changed, but the sample_config isn't updated
        # correctly, this test should help capture undeclared objects
        exceptions = {"same", "net_worth_target"}

        def check_for_none(obj, parent_path=""):
            for key, value in obj.items():
                if value is None and key not in exceptions:
                    pytest.fail(f"Value at path '{parent_path}.{key}' is None")
                elif isinstance(value, dict):
                    check_for_none(value, parent_path=f"{parent_path}.{key}")

        check_for_none(user.model_dump())
    except ValidationError as error:
        pytest.fail(f"Failed to validate sample user data: {error}")


def test_user_data():
    """Ensure user's data is valid"""
    with open(constants.CONFIG_PATH, encoding="utf-8") as file:
        user_data = cast(dict[str, Any], yaml.safe_load(file))
    assert user_data
    try:
        User(**user_data)
    except ValidationError as error:
        pytest.fail(f"Failed to validate user's data: {error}")


def test_sample_min_data():
    """Ensure sample min configs are valid"""
    for path in [
        constants.SAMPLE_MIN_CONFIG_INCOME_PATH,
        constants.SAMPLE_MIN_CONFIG_NET_WORTH_PATH,
    ]:
        with open(path, encoding="utf-8") as file:
            user_data = cast(dict[str, Any], yaml.safe_load(file))
        assert user_data
        try:
            User(**user_data)
        except ValidationError as error:
            pytest.fail(f"Failed to validate min config data: {error}")


def test_user_state_supported(sample_config_data):
    """If the user selects a state not supported,
    a ValidationError should be captured."""
    sample_config_data["state"] = "Mexico"
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**sample_config_data)


def test_either_income_or_net_worth():
    """User should provide at least one income profile or net worth"""
    data = {
        "age": 30,
        "spending_strategy": {
            "inflation_following": {
                "chosen": True,
                "profiles": [{"yearly_amount": 10000}],
            }
        },
    }
    with pytest.raises(ValidationError, match="1 validation error"):
        User(**data)
