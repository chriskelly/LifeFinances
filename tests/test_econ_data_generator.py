"""Testing for Models/econ_data_generator.py
run `python3 -m pytest` if VSCode Testing won't load
"""
# pylint: disable=protected-access

import math
import numpy as np
from models import econ_data_generator

MEAN_YIELD = 1.02
STDEV = .025
ANNUALIZED_LIMIT_UPPER = 1.02
ANNUALIZED_LIMIT_LOWER = 1.015
INTERVALS_PER_YEAR = 4

def test_brute_force():
    """Test Brute Force function"""
    year_qty = 10
    yield_ls = econ_data_generator._brute_force(iter_cnt=0, year_qty=year_qty,
                                                mean_yield=MEAN_YIELD, stdev=STDEV,
                                                lower_limit=ANNUALIZED_LIMIT_LOWER,
                                                upper_limit=ANNUALIZED_LIMIT_UPPER,
                                                intervals_per_year=INTERVALS_PER_YEAR)\
                                                    + 1
    assert len(yield_ls) == year_qty * INTERVALS_PER_YEAR
    annualized_return = pow(np.prod(yield_ls), 1 / year_qty)
    assert ANNUALIZED_LIMIT_LOWER <= annualized_return <= ANNUALIZED_LIMIT_UPPER

def test_generate_returns():
    """Test Generate Returns function"""
    intervals_per_run, runs = 40, 100
    all_returns = econ_data_generator._generate_returns(MEAN_YIELD, STDEV,
                                                        ANNUALIZED_LIMIT_UPPER,
                                                        ANNUALIZED_LIMIT_LOWER,
                                                        intervals_per_run, INTERVALS_PER_YEAR,
                                                        runs)
    assert len(all_returns) == runs
    assert len(all_returns[0]) == intervals_per_run
    # Confirm that the mean of the returns is within 20% of the mean range
    mean_yield_quarterly = pow(MEAN_YIELD, 1/INTERVALS_PER_YEAR)
    assert abs(mean_yield_quarterly-1 - np.mean(all_returns))\
            < 0.2 * (ANNUALIZED_LIMIT_UPPER - ANNUALIZED_LIMIT_LOWER)
    # Confirm that the standard deviation of the returns is within 10% of the standard deviation
    stdev_quarterly = STDEV / math.sqrt(INTERVALS_PER_YEAR)
    assert abs(stdev_quarterly - np.std(all_returns, ddof=1)) < 0.1 * stdev_quarterly
