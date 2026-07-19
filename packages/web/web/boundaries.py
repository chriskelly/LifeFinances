from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import cast

from core.streams import (
    Boundary,
    CalendarMonthBoundary,
    PersonAgeBoundary,
    PersonId,
    PersonMaxAgeBoundary,
)
from starlette.datastructures import FormData

KIND_NONE = "none"
KIND_NOW = "now"
KIND_CALENDAR = "calendar_month"
KIND_PERSON_AGE = "person_age"
KIND_PERSON_MAX_AGE = "person_max_age"

_ROW_RE = re.compile(r"^(?P<prefix>\w+)\[(?P<index>\d+)\]\.(?P<rest>.+)$")


def _int_or_none(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def _group_rows(
    pairs: Iterable[tuple[str, str]], prefix: str
) -> list[list[tuple[str, str]]]:
    rows: dict[int, list[tuple[str, str]]] = {}
    for key, value in pairs:
        match = _ROW_RE.match(key)
        if match is None or match.group("prefix") != prefix:
            continue
        rows.setdefault(int(match.group("index")), []).append(
            (match.group("rest"), value)
        )
    return [rows[index] for index in sorted(rows)]


def parse_boundary(
    *,
    kind: str,
    year: int | None = None,
    month: int | None = None,
    person: str | None = None,
    age_years: int | None = None,
    age_months: int | None = None,
    today: date,
) -> Boundary | None:
    """Turn flat form values into a `Boundary` (or `None`). `today` stamps "now"."""
    if kind == KIND_NONE:
        return None
    if kind == KIND_NOW:
        return CalendarMonthBoundary(year=today.year, month=today.month)
    if kind == KIND_CALENDAR:
        if year is None or month is None:
            raise ValueError("calendar boundary requires year and month")
        return CalendarMonthBoundary(year=year, month=month)
    if kind == KIND_PERSON_AGE:
        if person is None:
            raise ValueError("person_age boundary requires person")
        total_months = (age_years or 0) * 12 + (age_months or 0)
        return PersonAgeBoundary(person=cast(PersonId, person), age_months=total_months)
    if kind == KIND_PERSON_MAX_AGE:
        if person is None:
            raise ValueError("person_max_age boundary requires person")
        return PersonMaxAgeBoundary(person=cast(PersonId, person))
    raise ValueError(f"unknown boundary kind: {kind!r}")


def to_form(boundary: Boundary | None) -> dict[str, object]:
    """Render an existing boundary into template prefill state."""
    if boundary is None:
        return {"kind": KIND_NONE}
    if isinstance(boundary, CalendarMonthBoundary):
        return {"kind": KIND_CALENDAR, "year": boundary.year, "month": boundary.month}
    if isinstance(boundary, PersonAgeBoundary):
        return {
            "kind": KIND_PERSON_AGE,
            "person": boundary.person,
            "age_years": boundary.age_months // 12,
            "age_months": boundary.age_months % 12,
        }
    return {"kind": KIND_PERSON_MAX_AGE, "person": boundary.person}


def collect_indexed_rows(form: FormData, prefix: str) -> list[list[tuple[str, str]]]:
    """Group `prefix[i].rest` form fields into ordered rows of (rest, value) pairs."""
    return _group_rows(cast(Iterable[tuple[str, str]], form.multi_items()), prefix)


def row_scalar(row: list[tuple[str, str]], field: str, default: str = "") -> str:
    for key, value in row:
        if key == field:
            return value
    return default


def sub_rows(row: list[tuple[str, str]], prefix: str) -> list[list[tuple[str, str]]]:
    return _group_rows(row, prefix)


def row_boundary(
    row: list[tuple[str, str]], field_prefix: str, *, today: date
) -> Boundary | None:
    return parse_boundary(
        kind=row_scalar(row, f"{field_prefix}_kind", KIND_NONE),
        year=_int_or_none(row_scalar(row, f"{field_prefix}_year")),
        month=_int_or_none(row_scalar(row, f"{field_prefix}_month")),
        person=row_scalar(row, f"{field_prefix}_person") or None,
        age_years=_int_or_none(row_scalar(row, f"{field_prefix}_age_years")),
        age_months=_int_or_none(row_scalar(row, f"{field_prefix}_age_months")),
        today=today,
    )
