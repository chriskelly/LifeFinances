"""Testing for models/config/utils.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

from dataclasses import dataclass

import pytest
import yaml
from pydantic import ValidationError
from pytest_mock.plugin import MockerFixture

from app.data import constants
from app.models.config import attribute_filler, write_config_file


def test_attribute_filler():
    """The attribute_filler function should overwrite
    `None` values recursively, but not other values"""

    @dataclass
    class ThirdLevelObj:
        str1: str | None = None
        str2: str | None = None

    @dataclass
    class SecondLevelObj:
        third_lvl: ThirdLevelObj
        str1: str | None = None

    @dataclass
    class FirstLevelObj:
        second_lvl: SecondLevelObj
        str1: str | None = None

    # Test that it won't fill set values
    obj = FirstLevelObj(
        str1="World",
        second_lvl=SecondLevelObj(
            str1="World", third_lvl=ThirdLevelObj(str1="World", str2="World")
        ),
    )
    attribute_filler(obj=obj, attr="str1", fill_value="Hello")
    assert obj.str1 == "World"
    assert obj.second_lvl.third_lvl.str1 == "World"
    assert obj.second_lvl.third_lvl.str2 == "World"

    # Test that it will fill unspecified values
    obj = FirstLevelObj(second_lvl=SecondLevelObj(third_lvl=ThirdLevelObj()))
    attribute_filler(obj=obj, attr="str1", fill_value="Hello")
    assert obj.str1 == "Hello"
    assert obj.second_lvl.third_lvl.str1 == "Hello"
    assert obj.second_lvl.third_lvl.str2 is None


def test_write_config_file(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch):
    """Ensure write_config_file works as expected and fails when necessary"""
    with open(constants.SAMPLE_MIN_CONFIG_NET_WORTH_PATH, encoding="utf-8") as file:
        min_config = file.read()

    mock_open = mocker.MagicMock()
    monkeypatch.setattr("builtins.open", mock_open)

    # Test valid YAML
    write_config_file(min_config)
    mock_open.assert_called_once()

    # Test invalid YAML loading
    config_text = min_config.replace(":", "")
    with pytest.raises(TypeError):
        write_config_file(config_text)

    # Test invalid YAML format
    invalid_yaml = """
    key: value
    - item1
    - item2
    """
    with pytest.raises(yaml.YAMLError):
        write_config_file(invalid_yaml)

    # Test invalid config
    config_text = min_config.replace("age", "wrong_key")
    with pytest.raises(ValidationError):
        write_config_file(config_text)
