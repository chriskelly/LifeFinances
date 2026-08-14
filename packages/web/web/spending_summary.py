from __future__ import annotations

from dataclasses import dataclass

from simulation.result import SimulationResult

INITIAL_SPENDING_LABEL = "Initial spending"
WORST_CASE_SPENDING_LABEL = "Worst-case spending"


@dataclass(frozen=True)
class SpendingSummary:
    initial: float
    worst_case: float


def from_result(result: SimulationResult) -> SpendingSummary:
    """Summarize the total-spending series for the results panel.

    Row 0 of every percentile array is the lowest configured percentile
    (`result.percentiles` is sorted ascending). Month 0 is identical across
    rows, so `initial` is unambiguous.

    `worst_case` is the smallest month on that lowest-percentile row. Percentiles
    are computed independently per month, so the row is a cross-sectional
    envelope rather than a single simulated run — no individual run necessarily
    follows it.
    """
    lowest_percentile_row = result.withdrawals_total[0]
    return SpendingSummary(
        initial=float(lowest_percentile_row[0]),
        worst_case=float(lowest_percentile_row.min()),
    )
