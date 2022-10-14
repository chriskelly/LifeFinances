import math, time, random
from scipy import stats
import numpy as np
from models.skewDist import createSkewDist
from data import constants as const

DEBUG_LVL = 0

iter = 0

def generate_returns(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,columns):
    """
    What the hell is going in this function?    

    Parameters
    ----------
    mean : TYPE
        DESCRIPTION.
    stdev : TYPE
        DESCRIPTION.
    annual_high : TYPE
        DESCRIPTION.
    annual_low : TYPE
        DESCRIPTION.
    qty_per_column : int or float
        DESCRIPTION.
    qty_per_year : int or float
        Quantity per year, e.g. 4 for quarterly calculations
    columns : int or float
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    """
    global iter
    iter = 0
    # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    stdev = stdev / math.sqrt(qty_per_year) 
    mean = mean ** (1/qty_per_year)
    years_qty = math.ceil(qty_per_column/qty_per_year)
    def make_return_ls():
        annualized = 0
        while annualized < annual_low or annualized > annual_high:
            yield_ls = np.random.default_rng().normal(mean, stdev, years_qty*qty_per_year) # annualized test needs product in yearly multiples, even if years_qty*qty_per_year isn't equal to qty_per_column
            annualized = pow(np.prod(yield_ls), 1 / years_qty)
            global iter
            iter += 1
        return yield_ls - 1
    multi_returns = [make_return_ls()[:qty_per_column] for _ in range(columns)]
    if DEBUG_LVL >= 1:
        print(f'iter: {iter}')
        print(f'std mean: {abs(mean-1 - np.mean(multi_returns))}') # result should be 0.0
        print(f'std stdev: {abs(stdev - np.std(multi_returns, ddof=1))}') # result should be 0.0
    return multi_returns
    
    # trying to make it faster
def generate_returns_faster(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,columns):
    global iter
    iter = 0
    stdev = stdev / math.sqrt(qty_per_year) # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    mean = mean ** (1/qty_per_year)
    years_qty = math.ceil(qty_per_column/qty_per_year)
    def make_return_ls():
        annualized = 0
        while annualized < annual_low or annualized > annual_high:
            yield_ls = np.random.default_rng().normal(mean, stdev, years_qty*qty_per_year) # annualized test needs product in yearly multiples, even if years_qty*qty_per_year isn't equal to qty_per_column
            annualized = pow(np.prod(yield_ls), 1 / years_qty)
            global iter
            iter += 1
        return yield_ls - 1
    multi_returns = [make_return_ls()[:qty_per_column] for _ in range(columns)]
    if DEBUG_LVL >= 1:
        print(f'fast iter: {iter}')
        print(f'fast mean: {abs(mean-1 - np.mean(multi_returns))}') # result should be 0.0
        print(f'fast stdev: {abs(stdev - np.std(multi_returns, ddof=1))}') # result should be 0.0
    return multi_returns
    
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

def main(qty_per_column,qty_per_year,columns):
    generated_array =[]
    generated_array.append(generate_returns(const.EQUITY_MEAN, const.EQUITY_STDEV, const.EQUITY_ANNUAL_HIGH, const.EQUITY_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,columns))
    generated_array.append(generate_returns(const.BOND_MEAN, const.BOND_STDEV, const.BOND_ANNUAL_HIGH, const.BOND_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,columns))
    if DEBUG_LVL >= 1: start = time.perf_counter()
    generated_array.append(generate_returns(const.RE_MEAN, const.RE_STDEV, const.RE_ANNUAL_HIGH, const.RE_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,columns))
    if DEBUG_LVL >= 1: 
        mid = time.perf_counter()
        generate_returns_faster(const.RE_MEAN, const.RE_STDEV, const.RE_ANNUAL_HIGH, const.RE_ANNUAL_LOW,
                                        qty_per_column,qty_per_year,columns)
        end = time.perf_counter()
    generated_array.append(generate_skewd_inflation(const.INFLATION_MEAN, const.INFLATION_STDEV, const.INFLATION_SKEW,
                                    qty_per_column,qty_per_year,columns))
    if DEBUG_LVL >= 1: 
        print(f"std speed: {mid-start}")
        print(f"fast speed:{end-mid}")
    return generated_array

# main(270,4)