"""Testing for simulator.py
run `python -m pytest` if VSCode Testing won't load

"""
import sqlalchemy as db
import numpy as np
import simulator
from models import model
import data.constants as const
simulator.DEBUG_LVL = 0

# make sure model pulls default values for testing
model.ENGINE = db.create_engine(f'sqlite:///{const.DEFAULT_DB_LOC}')
test_mdl = model.Model()

def test_simulator_success_rate():
    """Ensure the simulator returns the same success rate as before.
    
    The success rate is confirmed experimentally for specific inflation arrays 
    applied to the default parameters. If this test fails, it indicates that 
    either the default parameters were changed or the simulator.main() [or any
    of its sub-functions] was modified in a way that changes the success rate
    for a given set of parameters.
    """
    rows = int((test_mdl.param_vals['calculate_til'] - model.TODAY_YR_QT)/.25)
    runs = 100
    returns = [[np.full(rows, const.EQUITY_MEAN-1)]*runs,
                [np.full(rows, const.BOND_MEAN-1)]*runs,
                [np.full(rows, const.RE_MEAN-1)]*runs,
                [np.linspace(start=1, stop=60+5*(n/runs), num=rows, endpoint=False)
                for n in range(runs)]]
    test_sim = simulator.Simulator(test_mdl.param_vals, override_dict={
                                                                    'monte_carlo_runs' : runs,
                                                                    'returns': returns})
    assert test_sim.main()['s_rate'] == 0.42

def test_val():
    """Test quarterly modifier in simulator.val function"""
    test_sim = simulator.Simulator(test_mdl.param_vals, override_dict={})
    test_sim.params['test_value'] = 15
    assert test_sim.val('test_value', quart_modifier='rate') == 2
    assert test_sim.val('test_value', quart_modifier='dollar') == 3.75
    assert test_sim.val('test_value', quart_modifier=None) == 15

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
