import math
import time
from scipy import stats
import random
import numpy as np
from skewDist import createSkewDist

DEBUG_LVL = 0

EQUITY_MEAN = 1.095
EQUITY_STDEV = .16
EQUITY_ANNUAL_HIGH = 1.09 # limits for annualized return check
EQUITY_ANNUAL_LOW = 1.07

BOND_MEAN = 1.02
BOND_STDEV = .025
BOND_ANNUAL_HIGH = 1.02
BOND_ANNUAL_LOW = 1.015

RE_MEAN = 1.11
RE_STDEV = .14
RE_ANNUAL_HIGH = 1.12
RE_ANNUAL_LOW = 1.08

INFLATION_MEAN = 1.037  # https://fred.stlouisfed.org/series/FPCPITOTLZGUSA#
INFLATION_STDEV = .027
INFLATION_ANNUAL_HIGH = 1.063
INFLATION_ANNUAL_LOW = 1.020
INFLATION_SKEW = 1.642

years_qty = 90


def generate_returns(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,columns, file_name):
    stdev = stdev / math.sqrt(qty_per_year) # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    mean = mean ** (1/qty_per_year)
    years_qty = math.ceil(qty_per_column/qty_per_year)
    iter = 0
    multi_returns = []
    for x in range(columns):
        annualized = 0
        while annualized < annual_low or annualized > annual_high:
            single_returns = []
            product = 1
            for _ in range(years_qty*qty_per_year): # annualized test needs product in yearly multiples, even if years_qty*qty_per_year isn't equal to qty_per_column
                return_yield = random.gauss(mean, stdev)
                single_returns.append(return_yield - 1)
                product = product * return_yield
            annualized = pow(product, 1 / years_qty)
            iter += 1
        multi_returns.append(single_returns[:qty_per_column])
    if DEBUG_LVL >= 1: print(iter)
    return multi_returns
    
    # trying to make it faster
def generate_returns_faster(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,columns, file_name):
    stdev = stdev / math.sqrt(qty_per_year) # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    mean = mean ** (1/qty_per_year)
    years_qty = math.ceil(qty_per_column/qty_per_year)
    def make_return_ls():
        annualized = 0
        while annualized < annual_low or annualized > annual_high:
            growth_ls = [random.gauss(mean, stdev) for _ in range(years_qty*qty_per_year)]# annualized test needs product in yearly multiples, even if years_qty*qty_per_year isn't equal to qty_per_column
            returns_ls = [growth-1 for growth in growth_ls]
            annualized = pow(np.prod(growth_ls), 1 / years_qty)
        return returns_ls
    multi_returns = [make_return_ls()[:qty_per_column] for _ in range(columns)]
    return multi_returns

def generate_inflation(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,columns, file_name):
    """similar functions, but it's easier to have inflations output be an array of the products rather than individual values"""
    stdev = stdev / math.sqrt(qty_per_year) # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    mean = mean ** (1/qty_per_year)
    years_qty = math.ceil(qty_per_column/qty_per_year)
    iter = 0
    multi_returns = []
    for x in range(columns):
        annualized = 0
        while annualized < annual_low or annualized > annual_high:
            single_returns = []
            product = 1
            for _ in range(years_qty*qty_per_year):
                return_yield = random.gauss(mean, stdev)
                product = product * return_yield
                single_returns.append(product)
            annualized = pow(product, 1 / years_qty)
            iter += 1
        multi_returns.append(single_returns[:qty_per_column])
    if DEBUG_LVL >= 1: print(iter)
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
    return multi_col_returns

def main(qty_per_column,qty_per_year,columns):
    generated_array =[]
    generated_array.append(generate_returns(EQUITY_MEAN, EQUITY_STDEV, EQUITY_ANNUAL_HIGH, EQUITY_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,columns, file_name="StockReturns.csv"))
    generated_array.append(generate_returns(BOND_MEAN, BOND_STDEV, BOND_ANNUAL_HIGH, BOND_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,columns, file_name="BondReturns.csv"))
    if DEBUG_LVL >= 1: start = time.perf_counter()
    generated_array.append(generate_returns(RE_MEAN, RE_STDEV, RE_ANNUAL_HIGH, RE_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,columns, file_name="REReturns.csv"))
    if DEBUG_LVL >= 1: 
        mid = time.perf_counter()
        speed_test = generate_returns_faster(RE_MEAN, RE_STDEV, RE_ANNUAL_HIGH, RE_ANNUAL_LOW,
                                        qty_per_column,qty_per_year,columns, file_name="REReturns.csv")
        end = time.perf_counter()
    # generated_array.append(generate_inflation(INFLATION_MEAN, INFLATION_STDEV, INFLATION_ANNUAL_HIGH, INFLATION_ANNUAL_LOW,
    #                                 qty_per_column,qty_per_year,columns, file_name="Inflation.csv"))
    generated_array.append(generate_skewd_inflation(INFLATION_MEAN, INFLATION_STDEV, INFLATION_SKEW,
                                    qty_per_column,qty_per_year,columns))
    if DEBUG_LVL >= 1: 
        print(f"standard: {mid-start}")
        print(f"fast:     {end-mid}")
    return generated_array

# main(270,4)