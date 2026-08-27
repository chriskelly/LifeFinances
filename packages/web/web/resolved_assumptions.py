from __future__ import annotations

import math

from simulation.result import ResolvedAssumptions, SimulationResult

UNAVAILABLE_MESSAGE = "Unavailable for current settings"
SOURCE_LABELS = {
    "manual": "Manual",
    "live": "Live",
    "cache": "Cached",
    "vendored": "Vendored fallback",
}


def annual_stock_log_volatility(
    assumptions: ResolvedAssumptions,
) -> float:
    return math.sqrt(assumptions.annual_stock_log_variance)


def from_result(result: SimulationResult | None) -> ResolvedAssumptions | None:
    """Project a simulation result to its resolved-assumptions snapshot.

    Owns the `None` check so callers never repeat `X if result is not None
    else None` at each of the home, market-assumptions, and results routes.
    """
    return result.resolved_assumptions if result is not None else None
