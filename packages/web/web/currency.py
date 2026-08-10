from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def format_usd(value: Decimal | int | float | str | None) -> str:
    """Format a dollar amount as USD with zero decimal places (e.g. ``$120,000``)."""
    if value is None or value == "":
        amount = Decimal(0)
    else:
        amount = Decimal(str(value))
    quantized = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"${quantized:,.0f}"


def parse_usd(raw: str | None) -> Decimal:
    """Parse a USD-ish string (``$120,000``, ``120000``, blanks) to a Decimal."""
    if raw is None:
        raise InvalidOperation("empty currency value")
    cleaned = raw.strip().replace("$", "").replace(",", "")
    if cleaned == "":
        raise InvalidOperation("empty currency value")
    return Decimal(cleaned)
