from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest
from web.percent import format_percent, parse_percent


def test_format_percent_uses_one_decimal_and_percent_sign() -> None:
    fraction = Decimal("0.035")

    assert format_percent(fraction) == "3.5%"


def test_format_percent_none_and_empty_are_zero() -> None:
    assert format_percent(None) == "0.0%"
    assert format_percent("") == "0.0%"


def test_parse_percent_accepts_formatted_and_plain() -> None:
    expected = Decimal("0.035")

    assert parse_percent("3.5%") == expected
    assert parse_percent("3.5") == expected
    assert parse_percent(" 3.5% ") == expected


def test_parse_percent_rejects_blank() -> None:
    with pytest.raises(InvalidOperation):
        parse_percent("")
    with pytest.raises(InvalidOperation):
        parse_percent("   ")
    with pytest.raises(InvalidOperation):
        parse_percent(None)
