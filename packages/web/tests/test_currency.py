from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest
from web.currency import format_usd, parse_usd


def test_format_usd_uses_dollar_sign_commas_and_zero_decimals() -> None:
    amount = Decimal("120000.49")

    assert format_usd(amount) == "$120,000"


def test_format_usd_none_and_empty_are_zero() -> None:
    assert format_usd(None) == "$0"
    assert format_usd("") == "$0"


def test_parse_usd_accepts_formatted_and_plain() -> None:
    expected = Decimal("150000")

    assert parse_usd("$150,000") == expected
    assert parse_usd("150000") == expected
    assert parse_usd(" 150,000 ") == expected


def test_parse_usd_rejects_blank() -> None:
    with pytest.raises(InvalidOperation):
        parse_usd("")
    with pytest.raises(InvalidOperation):
        parse_usd("   ")
    with pytest.raises(InvalidOperation):
        parse_usd(None)
