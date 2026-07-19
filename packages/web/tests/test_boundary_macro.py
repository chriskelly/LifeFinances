from web.app import templates


def _render(**kwargs) -> str:
    module = templates.get_template("_boundary.html").module
    return str(
        module.boundary_control(  # pyright: ignore[reportAttributeAccessIssue]
            "start", {"kind": "none"}, [("person1", "You")], **kwargs
        )
    )


def test_boundary_control_includes_now_when_allowed() -> None:
    assert 'value="now"' in _render(allow_now=True, allow_none=True)


def test_boundary_control_omits_now_by_default() -> None:
    assert 'value="now"' not in _render(allow_none=True)


def test_boundary_control_includes_max_age_when_allowed() -> None:
    assert 'value="person_max_age"' in _render(allow_max_age=True)


def test_boundary_control_names_use_prefix() -> None:
    markup = _render(allow_none=True)

    assert 'name="start_kind"' in markup
    assert 'name="start_year"' in markup
    assert 'name="start_person"' in markup
