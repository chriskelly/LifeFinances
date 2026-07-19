from datetime import date

import pytest
from core.streams import (
    CalendarMonthBoundary,
    PersonAgeBoundary,
    PersonMaxAgeBoundary,
)
from starlette.datastructures import FormData

from web import boundaries


def test_parse_boundary_none_returns_none() -> None:
    assert (
        boundaries.parse_boundary(kind=boundaries.KIND_NONE, today=date(2026, 7, 19))
        is None
    )


def test_parse_boundary_now_stamps_current_calendar_month() -> None:
    today = date(2026, 7, 19)

    result = boundaries.parse_boundary(kind=boundaries.KIND_NOW, today=today)

    assert result == CalendarMonthBoundary(year=today.year, month=today.month)


def test_parse_boundary_calendar_uses_year_and_month() -> None:
    expected = CalendarMonthBoundary(year=2030, month=4)

    result = boundaries.parse_boundary(
        kind=boundaries.KIND_CALENDAR,
        year=expected.year,
        month=expected.month,
        today=date(2026, 7, 19),
    )

    assert result == expected


def test_parse_boundary_person_age_combines_years_and_months() -> None:
    person = "person1"
    age_years = 65
    age_months = 2

    result = boundaries.parse_boundary(
        kind=boundaries.KIND_PERSON_AGE,
        person=person,
        age_years=age_years,
        age_months=age_months,
        today=date(2026, 7, 19),
    )

    assert result == PersonAgeBoundary(
        person=person, age_months=age_years * 12 + age_months
    )


def test_parse_boundary_person_max_age_is_symbolic() -> None:
    person = "person2"

    result = boundaries.parse_boundary(
        kind=boundaries.KIND_PERSON_MAX_AGE, person=person, today=date(2026, 7, 19)
    )

    assert result == PersonMaxAgeBoundary(person=person)


def test_parse_boundary_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unknown boundary kind"):
        boundaries.parse_boundary(kind="bogus", today=date(2026, 7, 19))


def test_collect_indexed_rows_groups_and_orders_by_index() -> None:
    first_label = "First"
    second_label = "Second"
    form = FormData(
        [
            ("jobs[1].label", second_label),
            ("jobs[0].label", first_label),
            ("portfolio", "ignored"),
        ]
    )

    rows = boundaries.collect_indexed_rows(form, "jobs")

    assert [boundaries.row_scalar(r, "label") for r in rows] == [
        first_label,
        second_label,
    ]


def test_sub_rows_extracts_nested_list() -> None:
    first_fraction = "0.5"
    second_fraction = "0.25"
    form = FormData(
        [
            ("jobs[0].label", "Eng"),
            ("jobs[0].sabbaticals[0].remaining_fraction", first_fraction),
            ("jobs[0].sabbaticals[1].remaining_fraction", second_fraction),
        ]
    )
    (row,) = boundaries.collect_indexed_rows(form, "jobs")

    sabbaticals = boundaries.sub_rows(row, "sabbaticals")

    assert [boundaries.row_scalar(s, "remaining_fraction") for s in sabbaticals] == [
        first_fraction,
        second_fraction,
    ]


def test_row_boundary_reads_prefixed_fields() -> None:
    today = date(2026, 7, 19)
    person = "person1"
    age_years = 50
    form = FormData(
        [
            ("jobs[0].start_kind", boundaries.KIND_PERSON_AGE),
            ("jobs[0].start_person", person),
            ("jobs[0].start_age_years", str(age_years)),
            ("jobs[0].start_age_months", "0"),
        ]
    )
    (row,) = boundaries.collect_indexed_rows(form, "jobs")

    result = boundaries.row_boundary(row, "start", today=today)

    assert result == PersonAgeBoundary(person=person, age_months=age_years * 12)
