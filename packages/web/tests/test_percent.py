from __future__ import annotations

from decimal import Decimal

import pytest
from web.percent import (
    INVALID_PERCENT_MESSAGE,
    format_percent,
    parse_optional_percent,
    parse_percent,
)


def test_format_percent_uses_one_decimal_and_percent_sign() -> None:
    # Display contract is intentionally pinned: one decimal place, trailing "%".
    assert format_percent(Decimal("0.035")) == "3.5%"
    assert format_percent(Decimal("0.0355")) == "3.6%"


def test_format_percent_none_and_empty_are_zero() -> None:
    zero_display = format_percent(Decimal(0))

    assert format_percent(None) == zero_display
    assert format_percent("") == zero_display


def test_parse_percent_accepts_formatted_and_plain() -> None:
    expected = Decimal("0.035")

    assert parse_percent("3.5%") == expected
    assert parse_percent("3.5") == expected
    assert parse_percent(" 3.5% ") == expected


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_parse_percent_rejects_blank_with_a_user_facing_message(
    raw: str | None,
) -> None:
    with pytest.raises(ValueError, match=INVALID_PERCENT_MESSAGE):
        parse_percent(raw)


def test_parse_percent_rejects_garbage_with_a_user_facing_message() -> None:
    with pytest.raises(ValueError, match=INVALID_PERCENT_MESSAGE):
        parse_percent("abc")


def test_parse_optional_percent_treats_absent_field_as_no_change() -> None:
    assert parse_optional_percent(None) is None
    assert parse_optional_percent("3.5%") == Decimal("0.035")
