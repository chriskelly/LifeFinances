from __future__ import annotations

import re
from decimal import Decimal

import pytest
from web.currency import INVALID_CURRENCY_MESSAGE, format_usd, parse_usd

_EXPECTED_ERROR = re.escape(INVALID_CURRENCY_MESSAGE)


def test_format_usd_rounds_cents_away_to_whole_dollars() -> None:
    # Display contract is intentionally pinned: leading "$", thousands commas,
    # no decimal places.
    assert format_usd(Decimal("120000.49")) == "$120,000"
    assert format_usd(Decimal("120000.50")) == "$120,001"


def test_format_usd_none_and_empty_are_zero() -> None:
    zero_display = format_usd(Decimal(0))

    assert format_usd(None) == zero_display
    assert format_usd("") == zero_display


def test_format_usd_keeps_the_maximum_currency_exactly() -> None:
    assert format_usd(Decimal("1e18")) == "$1,000,000,000,000,000,000"


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1_000_000_000_000_000_001"),
        Decimal("1e30"),
        Decimal("1e999999"),
        Decimal("1e1000000"),
    ],
)
def test_format_usd_clamps_values_above_the_maximum(value: Decimal) -> None:
    assert format_usd(value) == "$1,000,000,000,000,000,000+"


def test_format_usd_keeps_the_sign_when_clamping_a_negative_value() -> None:
    assert format_usd(Decimal("-1e30")) == "$-1,000,000,000,000,000,000+"


def test_parse_usd_accepts_formatted_and_plain() -> None:
    expected = Decimal("150000")

    assert parse_usd("$150,000") == expected
    assert parse_usd("150000") == expected
    assert parse_usd(" 150,000 ") == expected


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_parse_usd_rejects_blank_with_a_user_facing_message(raw: str | None) -> None:
    with pytest.raises(ValueError, match=_EXPECTED_ERROR):
        parse_usd(raw)


def test_parse_usd_rejects_garbage_with_a_user_facing_message() -> None:
    with pytest.raises(ValueError, match=_EXPECTED_ERROR):
        parse_usd("abc")


def test_parse_usd_accepts_the_maximum_value() -> None:
    assert parse_usd("1e18") == Decimal("1_000_000_000_000_000_000")


@pytest.mark.parametrize(
    "raw",
    [
        "1000000000000000001",
        "-1000000000000000001",
        "1e19",
        "-1e19",
        "1e999999",
        "1e1000000",
        "-1e1000000",
    ],
)
def test_parse_usd_rejects_values_beyond_the_maximum_magnitude(raw: str) -> None:
    with pytest.raises(ValueError, match=_EXPECTED_ERROR):
        parse_usd(raw)


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_parse_usd_rejects_non_finite_values(raw: str) -> None:
    with pytest.raises(ValueError, match=_EXPECTED_ERROR):
        parse_usd(raw)


def test_parse_usd_keeps_previous_when_submitted_display_matches() -> None:
    previous = Decimal("2500.50")
    echoed = format_usd(previous)

    assert parse_usd(echoed, previous=previous) == previous


def test_parse_usd_applies_edit_when_submitted_display_differs() -> None:
    previous = Decimal("2500.50")
    edited = "$2,500"

    assert parse_usd(edited, previous=previous) == Decimal("2500")


def test_parse_usd_keeps_oversized_previous_when_display_is_echoed() -> None:
    previous = Decimal("1e30")
    echoed = "$1,000,000,000,000,000,000+"

    assert parse_usd(echoed, previous=previous) == previous
