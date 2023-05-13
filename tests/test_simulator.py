"""Testing for simulator.py
run `python3 -m pytest` if VSCode Testing won't load

"""
import simulator

def test_step_quarterize():
    """Test step quarterizer function"""
    date_ls = [2025.25, 2025.75, 2026, 2026.5]
    first_val, increase_yield, start_date_idx, end_date_idx = 1, 1.1, 1, 3
    assert simulator.step_quarterize(date_ls, first_val, increase_yield,
                    start_date_idx, end_date_idx) == [1, 1.1, 1.1]
    date_ls, start_date_idx, end_date_idx = [2025.25], 0, 0
    assert simulator.step_quarterize(date_ls, first_val, increase_yield,
                    start_date_idx, end_date_idx) == [1]
    date_ls, start_date_idx, end_date_idx, increase_yield = [2025.25, 2025, 2026, 2026.5], 0, 3, 2
    assert simulator.step_quarterize(date_ls, first_val, increase_yield,
                    start_date_idx, end_date_idx) == [1, 2, 4, 4]
