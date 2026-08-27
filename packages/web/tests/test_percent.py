from __future__ import annotations

from decimal import Decimal

import pytest
from web.percent import (
    INVALID_PERCENT_MESSAGE,
    format_percent,
    format_percent_points,
    parse_optional_percent,
    parse_percent,
)


def test_format_percent_keeps_significant_decimals_without_forcing_one() -> None:
    # Display contract: trailing "%", variable precision, no fixed 1-dp rounding.
    assert format_percent(Decimal("0.035")) == "3.5%"
    assert format_percent(Decimal("0.0355")) == "3.55%"
    assert format_percent(Decimal("0.03")) == "3%"
    assert format_percent(Decimal(1)) == "100%"


def test_format_percent_strips_float_junk() -> None:
    # Intentionally pinned: fine-grid quantization must kill float noise.
    assert format_percent(Decimal("0.03100000001")) == "3.1%"


def test_format_percent_none_and_empty_are_zero() -> None:
    zero_display = format_percent(Decimal(0))

    assert format_percent(None) == zero_display
    assert format_percent("") == zero_display
    assert zero_display == "0%"


def test_parse_percent_accepts_formatted_and_plain() -> None:
    expected = Decimal("0.035")

    assert parse_percent("3.5%") == expected
    assert parse_percent("3.5") == expected
    assert parse_percent(" 3.5% ") == expected


def test_format_then_parse_preserves_multi_decimal_rates() -> None:
    stored = Decimal("0.0355")

    assert parse_percent(format_percent(stored)) == stored


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


def test_format_percent_points_is_format_percent_without_suffix() -> None:
    fraction = Decimal("0.0125")

    assert format_percent_points(fraction) == format_percent(fraction).removesuffix("%")
    assert format_percent_points(Decimal(0)) == format_percent(Decimal(0)).removesuffix(
        "%"
    )
    assert format_percent_points(Decimal("-0.025")) == format_percent(
        Decimal("-0.025")
    ).removesuffix("%")
