from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_HUNDRED = Decimal(100)
_ONE_DECIMAL = Decimal("0.1")

INVALID_PERCENT_MESSAGE = "Enter a percent, for example 3.5%"


def format_percent(value: Decimal | int | float | str | None) -> str:
    """Format a 0–1 fraction as a percent with one decimal (e.g. ``3.5%``)."""
    if value is None or value == "":
        amount = Decimal(0)
    else:
        amount = Decimal(str(value))
    as_percent = (amount * _HUNDRED).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP)
    return f"{as_percent}%"


def parse_percent(raw: str | None) -> Decimal:
    """Parse a percent-ish string (``3.5%``, ``3.5``) to a 0–1 fraction.

    Raises `ValueError` with a user-facing message on blank or unparseable input.
    """
    cleaned = (raw or "").strip().replace("%", "").replace(",", "")
    if cleaned == "":
        raise ValueError(INVALID_PERCENT_MESSAGE)
    try:
        return Decimal(cleaned) / _HUNDRED
    except InvalidOperation as exc:
        raise ValueError(INVALID_PERCENT_MESSAGE) from exc


def parse_optional_percent(raw: str | None) -> Decimal | None:
    """Parse a percent, treating an absent field as "leave the stored value alone"."""
    if raw is None:
        return None
    return parse_percent(raw)
