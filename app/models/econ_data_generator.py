"""Generates randomized economic data for stocks, bonds, real estate and inflation.

Required installations are detailed in requirements.txt.

This file contains the following functions:

    * main() - Generates and returns stock, bond, real estate, and inflation returns
"""

import math
import random
import numpy as np
from models.skew_dist import create_skew_dist
import data.constants as const

rng= np.random.default_rng() # instantiate a random generator

DEBUG_LVL = 0

def _brute_force(iter_cnt:int, year_qty:int, mean_yield:float, stdev:float,
                 lower_limit:float, upper_limit:float, intervals_per_year:int) -> np.ndarray:
    """Uses brute force to generate a list of yields with an annualized return
    that is within the given bounds
    
    Since values need to be tested against annualized limits, input may be larger
    than needed since years need to be tested in whole quantities, not fractional.
    Ex: You need 10 quarters (2.5 years) of data. year_qty must be 3

    Parameters
    ----------
    iter_cnt : int
        DESCRIPTION.
    year_qty : int
        DESCRIPTION.
    mean_yield : numeric
        DESCRIPTION.
    stdev : numeric
        DESCRIPTION.
    lower : numeric
        DESCRIPTION.
    upper : numeric
        DESCRIPTION.
    qty_per_year : int
        DESCRIPTION.

    Returns
    -------
    numpy.ndarray
        array of rates 

    """
    annualized_return = 0
    while annualized_return < lower_limit or annualized_return > upper_limit:
        yield_ls = rng.normal(mean_yield, stdev, year_qty*intervals_per_year)
        annualized_return = pow(np.prod(yield_ls), 1 / year_qty)
        iter_cnt += 1
    return yield_ls - 1

def _generate_returns(mean_yield, stdev, annual_high, annual_low, intervals_per_run, intervals_per_year,
                      runs) -> list[np.ndarray]:
    """Generate a time series of returns for each montecarlo run

    Parameters
    ----------
    mean_yield : TYPE
        Annualized mean.
    stdev : TYPE
        Annualized standard deviation.
    annual_high : TYPE
        DESCRIPTION.
    annual_low : TYPE
        DESCRIPTION.
    n_rows : int or float
        Number of rows per column.
    qty_per_year : int or float
        Quantity per year, e.g. 4 for quarterly calculations
    runs : int or float
        Number of monte carlo runs

    Returns
    -------
    multi_returns : list[ndarray]
        2D array. column is a lifetime/montecarlo run. rows are periods of time

    """
    iter_cnt = 0 # tracked for debugging. Init here to avoid scope issues
    # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    stdev = stdev / math.sqrt(intervals_per_year)
    mean_yield = mean_yield ** (1/intervals_per_year)
    year_qty = math.ceil(intervals_per_run/intervals_per_year)
    all_returns = [_brute_force(iter_cnt, year_qty, mean_yield, stdev, annual_low, annual_high,
                                 intervals_per_year)[:intervals_per_run] for _ in range(runs)]
    if DEBUG_LVL >= 1:
        print(f'iteration cnt: {iter_cnt}')
        print(f'std mean: {abs(mean_yield-1 - np.mean(all_returns))}') # result should be 0.0
        print(f'std stdev: {abs(stdev - np.std(all_returns, ddof=1))}') # result should be 0.0
    return all_returns

def _generate_skewd_inflation(mean_yield, stdev, skew, intervals_per_run, intervals_per_year, runs) -> list[list]:
    """Generate randomized inflation with a skew

    Args:
        mean_yield (_type_): _description_
        stdev (_type_): _description_
        skew (_type_): _description_
        qty_per_column (_type_): _description_
        qty_per_year (_type_): _description_
        runs (_type_): _description_

    Returns:
        list[list]: each list has inflation growing cumulatively
    """
    # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    stdev = stdev / math.sqrt(intervals_per_year)
    mean_yield = mean_yield ** (1/intervals_per_year)
    dist = create_skew_dist(mean_yield, stdev, skew, size=intervals_per_run*runs, debug=False)
    random.shuffle(dist) # create_skew_dist returns ordered items
    # convert to np array for split, then convert back to 2D list
    array = np.array(dist) 
    chunked_arrays = np.array_split(array, indices_or_sections=runs)
    inflation_lists = [list(array) for array in chunked_arrays]
    # convert individual inflation yields to cumulative inflation yields
    for i in range(runs):
        for j in range(1, intervals_per_run):
            inflation_lists[i][j] *= inflation_lists[i][j-1]
    if DEBUG_LVL >= 1:
        print(f'inflat mean: {abs(mean_yield - np.mean(dist))}') # result should be 0.0
        print(f'inflat stdev: {abs(stdev - np.std(dist, ddof=1))}') # result should be 0.0
    return inflation_lists

def main(intervals_per_run:int, intervals_per_year:int, runs:int) -> tuple[list[np.ndarray]]:
    """Generates and returns stock, bond, real estate, and inflation data

    Args:
        intervals_per_run (int): Quantity of time segments in each run
        intervals_per_year (int): Quantity of time segments in each year
        runs (int): How many runs in a simulation

    Returns:
        tuple[list[ndarray]]: 2D return arrays [Stock, Bond, Real Estate, Inflation]
    """
    stock_returns = _generate_returns(const.STOCK_MEAN, const.STOCK_STDEV,
                                            const.STOCK_ANNUAL_HIGH, const.STOCK_ANNUAL_LOW,
                                            intervals_per_run, intervals_per_year, runs)
    bond_returns = _generate_returns(const.BOND_MEAN, const.BOND_STDEV,
                                            const.BOND_ANNUAL_HIGH, const.BOND_ANNUAL_LOW,
                                            intervals_per_run, intervals_per_year, runs)
    real_estate_returns = _generate_returns(const.RE_MEAN, const.RE_STDEV, const.RE_ANNUAL_HIGH,
                                            const.RE_ANNUAL_LOW, intervals_per_run, intervals_per_year, runs)
    inflation = _generate_skewd_inflation(const.INFLATION_MEAN, const.INFLATION_STDEV,
                                                    const.INFLATION_SKEW, intervals_per_run,
                                                    intervals_per_year, runs)
    return stock_returns, bond_returns, real_estate_returns, inflation
