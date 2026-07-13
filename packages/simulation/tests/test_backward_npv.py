import numpy as np
from simulation.npv import backward_npv_including_current


def test_backward_npv_including_current_matches_hand_recurrence():
    real_series = np.array([10.0, 20.0, 30.0], dtype=np.float64)
    one_over_1_plus_r = 0.5  # extreme rate so arithmetic is obvious

    # Hand recurrence (last month → first), same as preprocess income pass:
    # m2: 0 * 0.5 + 30 = 30
    # m1: 30 * 0.5 + 20 = 35
    # m0: 35 * 0.5 + 10 = 27.5
    expected = np.array([27.5, 35.0, 30.0], dtype=np.float64)

    result = backward_npv_including_current(
        real_series, one_over_1_plus_r=one_over_1_plus_r
    )

    np.testing.assert_allclose(result, expected)
