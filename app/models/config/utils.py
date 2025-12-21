"""Utility functions for config module"""

from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import ValidationError

from app.data import constants
from app.models.config.user import User


def attribute_filler(obj, attr: str, fill_value):
    """Iterate recursively through obj and fills attr with fill_value

    Only fills if not specified (attr set to None)

    Args:
        obj (any)
        attr (str): the object attribute to be targeted
        fill_value (any): the value to change the attribute to
    """
    if hasattr(obj, "__dict__"):
        for field_name, field_value in vars(obj).items():
            # Confirm attribute is part of obj, but is set
            # to default None (consequense of user not providing it in config)
            if field_name == attr and not field_value:
                setattr(obj, attr, fill_value)
            else:
                attribute_filler(field_value, attr, fill_value)


def get_config(config_path: Path) -> User:
    """Populate the Python object from the YAML configuration file

    Args:
        config_path (Path)

    Returns:
        User
    """
    with open(config_path, encoding="utf-8") as file:  # pylint:disable=redefined-outer-name
        yaml_content = cast(dict[str, Any], yaml.safe_load(file))
    try:
        config = User(**yaml_content)
    except ValidationError as error:
        raise error

    # config.net_worth_target is considered global
    # and overwrites any net_worth_target value left unspecified
    if config.net_worth_target:
        attribute_filler(config, "net_worth_target", config.net_worth_target)

    return config


def read_config_file(config_path: Path = constants.CONFIG_PATH) -> str:
    """Reads the config file and returns the text"""
    with open(config_path, encoding="utf-8") as config_file:
        config_text = config_file.read()
    return config_text


def write_config_file(config_text: str, config_path: Path = constants.CONFIG_PATH):
    """Writes the config file after validation"""
    try:
        data_as_yaml = cast(dict[str, Any], yaml.safe_load(config_text))
        User(**data_as_yaml)
    except (yaml.YAMLError, TypeError) as error:
        print(f"Invalid YAML format: {error}")
        raise error
    except ValidationError as error:
        print(f"Invalid config: {error}")
        raise error
    with open(config_path, "w", encoding="utf-8") as config_file:
        config_file.write(config_text)
