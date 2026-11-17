from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from simulation.result import SimulationResult

from web.currency import format_usd
from web.percent import format_percent_points

WINDOW_MONTHS = 12

INITIAL_SPENDING_LABEL = "Initial spending"
INITIAL_SPENDING_TOOLTIP = (
    "Total spending in the first month of the plan. Every simulated run "
    "starts with this amount."
)
LOWEST_PERCENTILE_YEAR_LABEL = "Lowest-percentile year"
LOWEST_PERCENTILE_YEAR_TOOLTIP = (
    "The configured lowest percentile of each run's worst complete 12-month "
    "average. Partial windows at the start of the horizon are ignored."
)
MEDIAN_FINAL_YEAR_LABEL = "Median final year"
MEDIAN_FINAL_YEAR_TOOLTIP = (
    "The median across runs of the last complete 12-month average."
)
BAD_YEAR_LABEL = "Years below floor"
BAD_YEAR_TOOLTIP = (
    "Share of simulated runs whose worst complete 12-month average falls "
    "below the threshold."
)
BAD_MONTH_LABEL = "Months below floor"
BAD_MONTH_TOOLTIP = "Share of all simulated run-months below the threshold."
THRESHOLD_LABEL = "Threshold"
THRESHOLD_TOOLTIP = (
    "A monthly spending level in today's dollars. It only sets these odds; "
    "the simulation never reads it."
)
THRESHOLD_PROMPT = "Set a threshold to see how often spending falls below it."
UNAVAILABLE_VALUE = "unavailable"
LEVELS_TITLE = "Levels"
ODDS_TITLE = "Odds below floor"
APPLY_LABEL = "Apply"
BAD_YEAR_SUFFIX = "of runs"
BAD_MONTH_SUFFIX = "of months"


@dataclass(frozen=True)
class SpendingMetrics:
    initial: float | None
    lowest_percentile_year: float | None
    median_final_year: float | None
    bad_year_share: float | None
    bad_month_share: float | None


@dataclass(frozen=True)
class SpendingDeltas:
    initial: float | None
    lowest_percentile_year: float | None
    median_final_year: float | None
    bad_year_share: float | None
    bad_month_share: float | None


@dataclass(frozen=True)
class SpendingSummary:
    current: SpendingMetrics
    previous: SpendingMetrics | None
    deltas: SpendingDeltas
    threshold: Decimal | None


DeltaKind = Literal["usd", "pp"]
DeltaTone = Literal["better", "worse"]


@dataclass(frozen=True)
class DeltaMarker:
    symbol: str
    text: str
    tone: DeltaTone


def _difference(*, current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def deltas_for(
    *, current: SpendingMetrics, previous: SpendingMetrics | None
) -> SpendingDeltas:
    if previous is None:
        return SpendingDeltas(None, None, None, None, None)
    return SpendingDeltas(
        initial=_difference(current=current.initial, previous=previous.initial),
        lowest_percentile_year=_difference(
            current=current.lowest_percentile_year,
            previous=previous.lowest_percentile_year,
        ),
        median_final_year=_difference(
            current=current.median_final_year, previous=previous.median_final_year
        ),
        bad_year_share=_difference(
            current=current.bad_year_share, previous=previous.bad_year_share
        ),
        bad_month_share=_difference(
            current=current.bad_month_share, previous=previous.bad_month_share
        ),
    )


def delta_marker(
    *, value: float | None, kind: DeltaKind, higher_is_better: bool
) -> DeltaMarker | None:
    if value is None or value == 0:
        return None
    rising = value > 0
    sign = "+" if rising else "-"
    if kind == "usd":
        rendered = format_usd(abs(value))
        if rendered == format_usd(0):
            return None
        text = f"{sign}{rendered}/mo"
    else:
        rendered = format_percent_points(abs(value))
        if Decimal(rendered) == 0:
            return None
        text = f"{sign}{rendered} pp"
    tone: DeltaTone = "better" if rising == higher_is_better else "worse"
    return DeltaMarker(symbol="▲" if rising else "▼", text=text, tone=tone)


def metrics_for(
    *, result: SimulationResult, threshold: Decimal | None
) -> SpendingMetrics:
    if result.horizon_months == 0:
        return SpendingMetrics(None, None, None, None, None)
    initial = float(result.withdrawals_total[0, 0])
    matrix = result.withdrawals_total_by_run
    threshold_value = None if threshold is None else float(threshold)
    bad_month_share = (
        None if threshold_value is None else float(np.mean(matrix < threshold_value))
    )
    if result.horizon_months < WINDOW_MONTHS:
        return SpendingMetrics(initial, None, None, None, bad_month_share)

    # One mean per full 12-month window; shape (num_runs, horizon - 11).
    windows = sliding_window_view(matrix, WINDOW_MONTHS, axis=1).mean(axis=2)
    worst_year_by_run = windows.min(axis=1)
    lowest_year = float(np.percentile(worst_year_by_run, result.percentiles[0]))
    median_final = float(np.median(windows[:, -1]))
    bad_year_share = (
        None
        if threshold_value is None
        else float(np.mean(worst_year_by_run < threshold_value))
    )
    return SpendingMetrics(
        initial=initial,
        lowest_percentile_year=lowest_year,
        median_final_year=median_final,
        bad_year_share=bad_year_share,
        bad_month_share=bad_month_share,
    )


def build(
    *,
    result: SimulationResult,
    previous: SimulationResult | None = None,
    threshold: Decimal | None = None,
) -> SpendingSummary:
    current = metrics_for(result=result, threshold=threshold)
    previous_metrics = (
        None if previous is None else metrics_for(result=previous, threshold=threshold)
    )
    return SpendingSummary(
        current=current,
        previous=previous_metrics,
        deltas=deltas_for(current=current, previous=previous_metrics),
        threshold=threshold,
    )
