from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_HUNDRED = Decimal(100)
_ONE_DECIMAL = Decimal("0.1")


def format_percent(value: Decimal | int | float | str | None) -> str:
    """Format a 0–1 fraction as a percent with one decimal (e.g. ``3.5%``)."""
    if value is None or value == "":
        amount = Decimal(0)
    else:
        amount = Decimal(str(value))
    as_percent = (amount * _HUNDRED).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP)
    return f"{as_percent}%"


def parse_percent(raw: str | None) -> Decimal:
    """Parse a percent-ish string (``3.5%``, ``3.5``, blanks) to a 0–1 fraction."""
    if raw is None:
        raise InvalidOperation("empty percent value")
    cleaned = raw.strip().replace("%", "").replace(",", "")
    if cleaned == "":
        raise InvalidOperation("empty percent value")
    return Decimal(cleaned) / _HUNDRED
