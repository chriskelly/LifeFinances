from datetime import datetime

import numpy as np
from simulation.result import SimulationResult


def test_simulation_result_holds_per_run_arrays():
    num_runs, months = 3, 4
    expected_insufficient = 0
    zeros = np.zeros((num_runs, months), dtype=np.float64)

    result = SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=months,
        num_runs=num_runs,
        balance_start=zeros,
        withdrawals_essential=zeros,
        withdrawals_discretionary=zeros,
        withdrawals_general=zeros,
        withdrawals_total=zeros,
        savings_stock_allocation=zeros,
        num_runs_insufficient=expected_insufficient,
    )

    assert result.balance_start.shape == (num_runs, months)
    assert result.num_runs_insufficient == expected_insufficient
