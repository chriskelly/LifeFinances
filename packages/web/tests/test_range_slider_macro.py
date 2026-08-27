from typing import Any, cast

from web.app import templates


def _range_with_value() -> Any:
    # Jinja compiles macros onto a dynamically built module object, so the
    # attribute is invisible to static analysis; isolate the cast here.
    module = templates.get_template("_range_slider.html").module
    return cast(Any, module).range_with_value


def _render(
    *,
    name: str = "example",
    min: str = "0",
    max: str = "10",
    step: str = "1",
    value: str = "5",
    display: str | None = None,
    suffix: str = "",
) -> str:
    return str(
        _range_with_value()(
            name,
            min,
            max,
            step,
            value,
            display=display,
            suffix=suffix,
        )
    )


def test_range_with_value_wires_name_id_and_for() -> None:
    field_name = "risk_tolerance_at_20"
    markup = _render(name=field_name)

    assert f'id="{field_name}"' in markup
    assert f'name="{field_name}"' in markup
    assert f'for="{field_name}"' in markup


def test_range_with_value_renders_min_max_step_and_value() -> None:
    min_value = "-5"
    max_value = "5"
    step = "0.25"
    value = "1.25"
    markup = _render(min=min_value, max=max_value, step=step, value=value)

    assert f'min="{min_value}"' in markup
    assert f'max="{max_value}"' in markup
    assert f'step="{step}"' in markup
    assert f'value="{value}"' in markup


def test_range_with_value_appends_suffix_to_output_and_oninput() -> None:
    value = "1.25"
    suffix = "%"
    markup = _render(value=value, display=f"{value}{suffix}", suffix=suffix)

    assert f">{value}{suffix}</output>" in markup
    assert f"this.nextElementSibling.value = this.value + '{suffix}'" in markup
    assert markup.index('type="range"') < markup.index("<output")


def test_range_with_value_defaults_display_to_value_without_suffix() -> None:
    value = "12"
    markup = _render(value=value)

    assert f">{value}</output>" in markup
    assert "this.nextElementSibling.value = this.value + ''" in markup
