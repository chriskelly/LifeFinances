"""Generates randomized economic data for stocks, bonds, real estate and inflation.

Required installations are detailed in requirements.txt.

This file contains the following functions:

    * main() - Generates and returns stock, bond, real estate, and inflation returns
"""

import math
import random
import sys
from os import path
import git
import numpy as np
from models.skew_dist import create_skew_dist
import data.constants as const
git_root= git.Repo(path.abspath(__file__),
                   search_parent_directories=True).git.rev_parse('--show-toplevel')
sys.path.append(git_root)
#instantiate a random generator
rng= np.random.default_rng()

DEBUG_LVL = 0
data_path= path.join(git_root,'data/historic_data')

def _brute_force(n_iter:int, n_years:int, mean:float, stdev:float,
                 lower:float, upper:float, qty_per_year:int) -> np.ndarray:
    """
    Uses brute force to generate a list of yields with an annualized return
    that is within the given bounds

    Parameters
    ----------
    n_iter : int
        DESCRIPTION.
    n_years : int
        DESCRIPTION.
    mean : numeric
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
    annualized = 0
    while annualized < lower or annualized > upper:
        # annualized test needs product in yearly multiples,
        # even if years_qty*qty_per_year isn't equal to qty_per_column
        yield_ls = rng.normal(mean, stdev, n_years*qty_per_year)
        annualized = pow(np.prod(yield_ls), 1 / n_years)
        n_iter += 1
    return yield_ls - 1

def _generate_returns(mean, stdev, annual_high, annual_low,n_rows, qty_per_year,
                      columns) -> list[np.ndarray]:
    """
    Generate a time series of returns for each montecarlo run

    Parameters
    ----------
    mean : TYPE
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
    columns : int or float
        Number of columns, which means the number of monte carlo runs

    Returns
    -------
    multi_returns : list[ndarray]
        2D array. column is a lifetime/montecarlo run. rows are periods of time

    """
    n_iter = 0
    # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    stdev = stdev / math.sqrt(qty_per_year)
    mean = mean ** (1/qty_per_year)
    n_years = math.ceil(n_rows/qty_per_year)
    multi_returns = [_brute_force(n_iter, n_years, mean, stdev, annual_low, annual_high,
                                 qty_per_year)[:n_rows] for _ in range(columns)]
    if DEBUG_LVL >= 1:
        print(f'n_iter: {n_iter}')
        print(f'std mean: {abs(mean-1 - np.mean(multi_returns))}') # result should be 0.0
        print(f'std stdev: {abs(stdev - np.std(multi_returns, ddof=1))}') # result should be 0.0
    return multi_returns

def _generate_skewd_inflation(mean, stdev, skew,qty_per_column,qty_per_year,columns) -> list[list]:
    """Generate randomized inflation with a skew

    Args:
        mean (_type_): _description_
        stdev (_type_): _description_
        skew (_type_): _description_
        qty_per_column (_type_): _description_
        qty_per_year (_type_): _description_
        columns (_type_): _description_

    Returns:
        list[list]: 2D array of returns
    """
    # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    stdev = stdev / math.sqrt(qty_per_year)
    mean = mean ** (1/qty_per_year)
    dist = create_skew_dist(mean,stdev,skew,size=qty_per_column*columns,debug=False)
    random.shuffle(dist) # createSkewDist returns ordered items
    array = np.array(dist)
    chunked_arrays = np.array_split(array,indices_or_sections=columns)
    multi_col_returns = [list(array) for array in chunked_arrays]
    for multi_col_idx in range(columns):
        single_col_idx = 1
        while single_col_idx<qty_per_column:
            multi_col_returns[multi_col_idx][single_col_idx]\
                *= multi_col_returns[multi_col_idx][single_col_idx-1]
            single_col_idx+=1
    if DEBUG_LVL >= 1:
        print(f'inflat mean: {abs(mean - np.mean(dist))}') # result should be 0.0
        print(f'inflat stdev: {abs(stdev - np.std(dist, ddof=1))}') # result should be 0.0
    return multi_col_returns

def main(n_rows:int, qty_per_year:int, columns:int) -> list[list[np.ndarray]]:
    """Generates and returns stock, bond, real estate, and inflation returns

    Args:
        n_rows (int): Quantity of time segments in each run
        qty_per_year (int): Quantity of time segments in each year
        columns (int): How many runs in a simulation

    Returns:
        tuple[list[ndarray]]: 2D return arrays [Stock, Bond, Real Estate, Inflation]
    """
    stock_returns = _generate_returns(const.EQUITY_MEAN, const.EQUITY_STDEV,
                                            const.EQUITY_ANNUAL_HIGH, const.EQUITY_ANNUAL_LOW,
                                            n_rows,qty_per_year,columns)
    bond_returns = _generate_returns(const.BOND_MEAN, const.BOND_STDEV,
                                            const.BOND_ANNUAL_HIGH, const.BOND_ANNUAL_LOW,
                                            n_rows,qty_per_year,columns)
    real_estate_returns = _generate_returns(const.RE_MEAN, const.RE_STDEV, const.RE_ANNUAL_HIGH,
                                            const.RE_ANNUAL_LOW, n_rows,qty_per_year,columns)
    inflation = _generate_skewd_inflation(const.INFLATION_MEAN, const.INFLATION_STDEV,
                                                    const.INFLATION_SKEW, n_rows,
                                                    qty_per_year, columns)
    return stock_returns, bond_returns, real_estate_returns, inflation
