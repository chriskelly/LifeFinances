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
    """Summarize total-spending series for the results panel.

    Month 0 is deterministic across percentile rows; worst-case is the minimum
    along the lowest-percentile path over the full horizon.
    """
    total = result.withdrawals_total
    return SpendingSummary(
        initial=float(total[0, 0]),
        worst_case=float(total[0].min()),
    )
