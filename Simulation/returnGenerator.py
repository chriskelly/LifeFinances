import pandas
import random

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

INFLATION_MEAN = 1.03
INFLATION_STDEV = .025
INFLATION_ANNUAL_HIGH = 1.06
INFLATION_ANNUAL_LOW = 1.02

generate_qty = 5000
years_qty = 90


def generate(mean, stdev, annual_high, annual_low, file_name):
    iter = 0
    multi_returns = {}
    for x in range(generate_qty):
        annualized = 0
        while annualized < annual_low or annualized > annual_high:
            single_returns = []
            product = 1
            for _ in range(years_qty):
                return_yield = random.gauss(mean, stdev)
                single_returns.append(return_yield - 1)
                product = product * return_yield
            annualized = pow(product, 1 / years_qty)
            iter += 1
        multi_returns[x] = single_returns
    print(iter)
    data = pandas.DataFrame(multi_returns)
    data.to_csv(file_name)


generate(EQUITY_MEAN, EQUITY_STDEV, EQUITY_ANNUAL_HIGH, EQUITY_ANNUAL_LOW, file_name="StockReturns.csv")
generate(BOND_MEAN, BOND_STDEV, BOND_ANNUAL_HIGH, BOND_ANNUAL_LOW, file_name="BondReturns.csv")
generate(RE_MEAN, RE_STDEV, RE_ANNUAL_HIGH, RE_ANNUAL_LOW, file_name="REReturns.csv")
generate(INFLATION_MEAN, INFLATION_STDEV, INFLATION_ANNUAL_HIGH, INFLATION_ANNUAL_LOW, file_name="InflationReturns.csv")

