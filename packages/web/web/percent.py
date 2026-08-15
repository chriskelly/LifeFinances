from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_HUNDRED = Decimal(100)
# Fine grid on the *percent* value (not the 0–1 fraction) kills float noise
# without forcing a fixed display precision.
_PERCENT_GRID = Decimal("0.000001")

INVALID_PERCENT_MESSAGE = "Enter a percent, for example 3.5%"


def format_percent(value: Decimal | int | float | str | None) -> str:
    """Format a 0–1 fraction as a percent with variable precision (e.g. ``3.55%``).

    Quantizes to a fine grid then strips trailing zeros so float junk like
    ``3.100000001%`` never appears, without rounding meaningful decimals away.
    """
    if value is None or value == "":
        amount = Decimal(0)
    else:
        amount = Decimal(str(value))
    as_percent = (amount * _HUNDRED).quantize(_PERCENT_GRID, rounding=ROUND_HALF_UP)
    normalized = as_percent.normalize()
    # Decimal.normalize() can switch to scientific notation for whole numbers
    # (e.g. 100 -> 1E+2); format with fixed-point then strip trailing zeros.
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text}%"


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
