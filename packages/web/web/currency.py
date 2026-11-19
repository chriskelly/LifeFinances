from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

INVALID_CURRENCY_MESSAGE = "Enter a dollar amount, for example $120,000"

# Mirrors the le=Decimal("1e18") bound on Plan.summary_spending_threshold.
# Inputs beyond it are rejected at the shared form boundary; stored values
# beyond it are old data and must still render.
MAX_USD = Decimal("1e18")
_MAX_USD_TEXT = f"{MAX_USD:,.0f}"


def format_usd(value: Decimal | int | float | str | None) -> str:
    """Format a dollar amount as USD with zero decimal places (e.g. ``$120,000``).

    Finite values whose magnitude exceeds ``MAX_USD`` render as
    ``$1,000,000,000,000,000,000+``, keeping a negative sign. Non-finite input
    is out of contract.
    """
    if value is None or value == "":
        amount = Decimal(0)
    else:
        amount = Decimal(str(value))
    # abs(NaN) raises, so gate on is_finite before the magnitude check.
    if amount.is_finite() and abs(amount) > MAX_USD:
        sign = "-" if amount < 0 else ""
        return f"${sign}{_MAX_USD_TEXT}+"
    quantized = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"${quantized:,.0f}"


def parse_usd(raw: str | None, *, previous: Decimal | None = None) -> Decimal:
    """Parse a USD-ish string (``$120,000``, ``120000``) to a Decimal.

    When ``previous`` is set and ``raw`` exactly equals ``format_usd(previous)``,
    return ``previous`` unchanged so an autosave that echoes the display value
    does not silently mutate stored cents. That echo check runs before the
    bound, so a stored oversized value can be re-saved unchanged.

    Raises `ValueError` with a user-facing message on blank, unparseable,
    non-finite, or beyond-``MAX_USD``-magnitude input.
    """
    cleaned = (raw or "").strip().replace("$", "").replace(",", "")
    if cleaned == "":
        raise ValueError(INVALID_CURRENCY_MESSAGE)
    if previous is not None and (raw or "").strip() == format_usd(previous):
        return previous
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(INVALID_CURRENCY_MESSAGE) from exc
    # Negative values within the bound stay model-rejected (currency fields'
    # ge=0).
    if not amount.is_finite() or abs(amount) > MAX_USD:
        raise ValueError(INVALID_CURRENCY_MESSAGE)
    return amount
