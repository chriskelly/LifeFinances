import math
import time
import pandas
import random
import numpy as np

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

years_qty = 90


def generate_returns(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,generate_qty, file_name):
    stdev = stdev / math.sqrt(qty_per_year) # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    mean = mean ** (1/qty_per_year)
    years_qty = math.ceil(qty_per_column/qty_per_year)
    iter = 0
    multi_returns = []
    for x in range(generate_qty):
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
    print(iter)
    return multi_returns
    #data = pandas.DataFrame(multi_returns)
    #data.to_csv(file_name)
    #return data
    
    # trying to make it faster
def generate_returns_faster(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,generate_qty, file_name):
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
    multi_returns = [make_return_ls()[:qty_per_column] for _ in range(generate_qty)]
    return multi_returns

def generate_inflation(mean, stdev, annual_high, annual_low,qty_per_column,qty_per_year,generate_qty, file_name):
    """similar functions, but it's easier to have inflations output be an array of the products rather than individual values"""
    stdev = stdev / math.sqrt(qty_per_year) # Standard Deviation of Quarterly Returns = Annualized Standard Deviation / Sqrt(4)
    mean = mean ** (1/qty_per_year)
    years_qty = math.ceil(qty_per_column/qty_per_year)
    iter = 0
    multi_returns = []
    for x in range(generate_qty):
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
    print(iter)
    return multi_returns
    #data = pandas.DataFrame(multi_returns)
    #data.to_csv(file_name)
    #return data

def main(qty_per_column,qty_per_year,generate_qty):
    generated_array =[]
    generated_array.append(generate_returns(EQUITY_MEAN, EQUITY_STDEV, EQUITY_ANNUAL_HIGH, EQUITY_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,generate_qty, file_name="StockReturns.csv"))
    generated_array.append(generate_returns(BOND_MEAN, BOND_STDEV, BOND_ANNUAL_HIGH, BOND_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,generate_qty, file_name="BondReturns.csv"))
    start = time.perf_counter()
    generated_array.append(generate_returns(RE_MEAN, RE_STDEV, RE_ANNUAL_HIGH, RE_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,generate_qty, file_name="REReturns.csv"))
    mid = time.perf_counter()
    speed_test = generate_returns_faster(RE_MEAN, RE_STDEV, RE_ANNUAL_HIGH, RE_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,generate_qty, file_name="REReturns.csv")
    end = time.perf_counter()
    generated_array.append(generate_inflation(INFLATION_MEAN, INFLATION_STDEV, INFLATION_ANNUAL_HIGH, INFLATION_ANNUAL_LOW,
                                    qty_per_column,qty_per_year,generate_qty, file_name="Inflation.csv"))
    print(f"standard: {mid-start}")
    print(f"fast:     {end-mid}")
    return generated_array

# main(270,4)