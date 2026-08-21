from __future__ import annotations

import math

from simulation.result import ResolvedAssumptions

from web import forms

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


def planning_preset_label(preset: str) -> str:
    return forms.PLANNING_PRESET_LABELS[preset]
