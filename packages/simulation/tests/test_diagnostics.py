import math

import numpy as np
from simulation.diagnostics import (
    RRA_INFINITE_SENTINEL,
    empty_diagnostics,
    rra_for_diagnostics,
)


def test_rra_for_diagnostics_replaces_infinity_with_sentinel() -> None:
    finite = 4.0
    engine_rra = np.array([math.inf, finite], dtype=np.float64)

    displayed = rra_for_diagnostics(engine_rra)

    np.testing.assert_array_equal(
        displayed, np.array([RRA_INFINITE_SENTINEL, finite], dtype=np.float64)
    )
    assert math.isinf(engine_rra[0])


def test_empty_diagnostics_series_match_requested_horizon() -> None:
    months = 3

    diagnostics = empty_diagnostics(months=months)

    assert diagnostics.rra_by_month.shape == (months,)
    assert diagnostics.expected_savings_stock_fraction.shape == (months,)
    assert diagnostics.legacy_stock_allocation == 0.0
