import math, time, random
from scipy import stats
import numpy as np, pandas as pd
from os import path
# from numba import jit

import git, sys
git_root= git.Repo(path.abspath(''),
                   search_parent_directories=True).git.rev_parse('--show-toplevel')
sys.path.append(git_root)
from models.skewDist import createSkewDist
from data import constants as const
#instantiate a random generator
rng= np.random.default_rng()

DEBUG_LVL = 0
data_path= path.join(git_root,'data/historic_data')



def brute_force(n_iter, n_years, mean, stdev, lower, upper, qty_per_year):
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
    yield_ls : numpy.array
        DESCRIPTION.

    """
    annualized = 0
    while annualized < lower or annualized > upper:
        # annualized test needs product in yearly multiples, even if years_qty*qty_per_year isn't equal to qty_per_column
        yield_ls = rng.normal(mean, stdev, n_years*qty_per_year) 
        annualized = pow(np.prod(yield_ls), 1 / n_years)
        n_iter += 1
    return yield_ls - 1

def generate_returns(mean, stdev, annual_high, annual_low,n_rows,qty_per_year,columns):
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
    multi_returns : list
        2D array. column is a lifetime/montecarlo run. rows are periods of time

    """
    n_iter = 0
    # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    stdev = stdev / math.sqrt(qty_per_year) 
    mean = mean ** (1/qty_per_year)
    n_years = math.ceil(n_rows/qty_per_year)
    multi_returns = [brute_force(n_iter, n_years, mean, stdev, annual_low, annual_high, qty_per_year)[:n_rows] 
                     for _ in range(columns)]
    if DEBUG_LVL >= 1:
        print(f'n_iter: {n_iter}')
        print(f'std mean: {abs(mean-1 - np.mean(multi_returns))}') # result should be 0.0
        print(f'std stdev: {abs(stdev - np.std(multi_returns, ddof=1))}') # result should be 0.0
    return multi_returns
    
    # trying to make it faster
def generate_returns_faster(mean, stdev, annual_high, annual_low,n_rows,qty_per_year,columns):
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
    multi_returns : list
        2D array. column is a lifetime/montecarlo run. rows are periods of time

    """
    n_iter = 0
    # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    stdev = stdev / math.sqrt(qty_per_year) 
    mean = mean ** (1/qty_per_year)
    n_years = math.ceil(n_rows/qty_per_year)
    multi_returns = [brute_force(n_iter, n_years, mean, stdev, annual_low, annual_high, qty_per_year)[:n_rows] 
                     for _ in range(columns)]
    if DEBUG_LVL >= 1:
        print(f'n_iter: {n_iter}')
        print(f'std mean: {abs(mean-1 - np.mean(multi_returns))}') # result should be 0.0
        print(f'std stdev: {abs(stdev - np.std(multi_returns, ddof=1))}') # result should be 0.0
    return multi_returns

# @jit    
def generate_skewd_inflation(mean, stdev, skew,qty_per_column,qty_per_year,columns):
    stdev = stdev / math.sqrt(qty_per_year) # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    mean = mean ** (1/qty_per_year)
    dist = createSkewDist(mean,stdev,skew,size=qty_per_column*columns,debug=False)
        #TODO: 25% of generated values are negative inflation
    random.shuffle(dist) # createSkewDist returns ordered items
    array = np.array(dist)
    chunked_arrays = np.array_split(array,indices_or_sections=columns)
    multi_col_returns = [list(array) for array in chunked_arrays]
    for multi_col_idx in range(columns):
        single_col_idx = 1
        while single_col_idx<qty_per_column:
            multi_col_returns[multi_col_idx][single_col_idx] *= multi_col_returns[multi_col_idx][single_col_idx-1]
            single_col_idx+=1
    if DEBUG_LVL >= 1:
        print(f'inflat mean: {abs(mean - np.mean(dist))}') # result should be 0.0
        print(f'inflat stdev: {abs(stdev - np.std(dist, ddof=1))}') # result should be 0.0
    return multi_col_returns

def main(n_rows,qty_per_year,columns):
    generated_array =[]
    generated_array.append(generate_returns(const.EQUITY_MEAN, const.EQUITY_STDEV, const.EQUITY_ANNUAL_HIGH, const.EQUITY_ANNUAL_LOW,
                                    n_rows,qty_per_year,columns))
    generated_array.append(generate_returns(const.BOND_MEAN, const.BOND_STDEV, const.BOND_ANNUAL_HIGH, const.BOND_ANNUAL_LOW,
                                    n_rows,qty_per_year,columns))
    if DEBUG_LVL >= 1: start = time.perf_counter()
    generated_array.append(generate_returns(const.RE_MEAN, const.RE_STDEV, const.RE_ANNUAL_HIGH, const.RE_ANNUAL_LOW,
                                    n_rows,qty_per_year,columns))
    if DEBUG_LVL >= 1: 
        mid = time.perf_counter()
        generate_returns_faster(const.RE_MEAN, const.RE_STDEV, const.RE_ANNUAL_HIGH, const.RE_ANNUAL_LOW,
                                    n_rows,qty_per_year,columns)
        end = time.perf_counter()
    generated_array.append(generate_skewd_inflation(const.INFLATION_MEAN, const.INFLATION_STDEV, const.INFLATION_SKEW,
                                    n_rows,qty_per_year,columns))
    if DEBUG_LVL >= 1: 
        print(f"std speed: {mid-start}")
        print(f"fast speed:{end-mid}")
    return generated_array

# main(270,4)