from datetime import datetime

import numpy as np
from simulation.aggregate import build_public_result
from simulation.composition import WealthBySource
from simulation.result import RAW_ARRAY_FIELDS, RawSimulationResult

_NUM_RUNS = 3
_MONTHS = 2
# One distinct 2-D array per raw field so a swapped field->field mapping in
# build_public_result cannot pass. Runs ascend so percentiles [0, 50, 100]
# pick min/median/max deterministically.
_BASE = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], dtype=np.float64)
_RAW_ARRAYS = {
    field: _BASE * float(index + 1) for index, field in enumerate(RAW_ARRAY_FIELDS)
}


def _raw() -> RawSimulationResult:
    return RawSimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=_MONTHS,
        num_runs=_NUM_RUNS,
        num_runs_insufficient=0,
        balance_start=_RAW_ARRAYS["balance_start"],
        withdrawals_essential=_RAW_ARRAYS["withdrawals_essential"],
        withdrawals_discretionary=_RAW_ARRAYS["withdrawals_discretionary"],
        withdrawals_general=_RAW_ARRAYS["withdrawals_general"],
        withdrawals_total=_RAW_ARRAYS["withdrawals_total"],
        savings_stock_allocation=_RAW_ARRAYS["savings_stock_allocation"],
    )


def test_build_public_result_reduces_each_array_field_along_runs():
    percentiles = [0, 50, 100]  # min / median / max
    start_month = (2026, 1)
    raw = _raw()
    composition = WealthBySource(
        job=np.zeros(_MONTHS, dtype=np.float64),
        social_security=np.zeros(_MONTHS, dtype=np.float64),
        pension=np.zeros(_MONTHS, dtype=np.float64),
        manual=np.zeros(_MONTHS, dtype=np.float64),
    )

    result = build_public_result(
        raw,
        percentiles=percentiles,
        composition=composition,
        start_month=start_month,
    )

    for field, raw_array in _RAW_ARRAYS.items():
        reduced = getattr(result, field)
        assert reduced.shape == (len(percentiles), _MONTHS)
        np.testing.assert_allclose(
            reduced, np.percentile(raw_array, percentiles, axis=0)
        )

    # Hand-derived: for 3 runs ascending per column, [0, 50, 100] percentiles are
    # exactly min/median/max, i.e. the raw rows unchanged — independent of numpy.
    first_field = RAW_ARRAY_FIELDS[0]
    np.testing.assert_allclose(getattr(result, first_field), _RAW_ARRAYS[first_field])
    assert result.percentiles == percentiles
    assert result.num_runs == _NUM_RUNS
    assert result.start_month == start_month
