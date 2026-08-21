from typing import Any, cast

from web.app import templates

from web import boundaries, forms


def _boundary_control() -> Any:
    # Jinja compiles macros onto a dynamically built module object, so the
    # attribute is invisible to static analysis; isolate the cast here.
    module = templates.get_template("_boundary.html").module
    return cast(Any, module).boundary_control


def _render(*, current: dict | None = None, **kwargs) -> str:
    return str(
        _boundary_control()(
            "start",
            current if current is not None else {"kind": boundaries.KIND_NONE},
            [("person1", "You")],
            **kwargs,
        )
    )


def test_boundary_control_includes_now_when_allowed() -> None:
    assert f'value="{boundaries.KIND_NOW}"' in _render(allow_now=True, allow_none=True)


def test_boundary_control_omits_now_by_default() -> None:
    assert f'value="{boundaries.KIND_NOW}"' not in _render(allow_none=True)


def test_boundary_control_includes_max_age_when_allowed() -> None:
    assert f'value="{boundaries.KIND_PERSON_MAX_AGE}"' in _render(allow_max_age=True)


def test_boundary_control_omits_max_age_by_default() -> None:
    assert f'value="{boundaries.KIND_PERSON_MAX_AGE}"' not in _render()


def test_boundary_control_names_use_prefix() -> None:
    markup = _render(allow_none=True)

    assert 'name="start_kind"' in markup
    assert 'name="start_year"' in markup
    assert 'name="start_person"' in markup
    assert "data-prefix" not in markup


def test_boundary_control_calendar_month_uses_abbreviated_month_select() -> None:
    expected_month = 8
    markup = _render(
        allow_none=True,
        current={
            "kind": boundaries.KIND_CALENDAR,
            "year": 2030,
            "month": expected_month,
        },
    )

    assert 'name="start_month"' in markup
    assert 'type="number" name="start_month"' not in markup
    for month_number, label in forms.MONTH_ABBREVIATIONS:
        assert f'value="{month_number}"' in markup
        assert f">{label}</option>" in markup
    assert f'value="{expected_month}" selected' in markup
