"""Testing for simulator.py
run `python3 -m pytest` if VSCode Testing won't load

"""
import numpy as np
import simulator
from models import model
import data.constants as const
simulator.DEBUG_LVL = 1

test_user = model.Model().user

def test_simulator_success_rate():
    """Ensure the simulator returns the same success rate as before.
    
    The success rate is confirmed experimentally for specific inflation arrays 
    applied to the default parameters. If this test fails, it indicates that 
    either the default parameters were changed or the simulator.main() [or any
    of its sub-functions] was modified in a way that changes the success rate
    for a given set of parameters.
    """
    rows = int((test_user.calculate_til - model.TODAY_YR_QT)/.25)
    runs = 100
    returns = [[np.full(rows, const.EQUITY_MEAN-1)]*runs,
                [np.full(rows, const.BOND_MEAN-1)]*runs,
                [np.full(rows, const.RE_MEAN-1)]*runs,
                [np.linspace(start=1, stop=35+5*(n/runs), num=rows, endpoint=False)
                for n in range(runs)]]
    test_sim = simulator.Simulator(test_user, override_options={
                                                            'monte_carlo_runs' : runs,
                                                            'returns': returns})
    res = test_sim.run()
    assert res['s_rate'] == 0.59

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
