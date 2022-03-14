import pandas
import random

Equity_Mean = 1.095
Equity_Stdev = .16
Equity_Annual_High = 1.09
Equity_Annual_Low = 1.07

Bond_Mean = 1.02
Bond_Stdev = .025
Bond_Annual_High = 1.02
Bond_Annual_Low = 1.015

RE_Mean = 1.11
RE_Stdev = .14
RE_Annual_High = 1.12
RE_Annual_Low = 1.08

generate_qty = 5000
years_qty = 90


def generate_returns(mean, stdev, annual_high, annual_low, file_name):
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


generate_returns(Equity_Mean, Equity_Stdev, Equity_Annual_High, Equity_Annual_Low, file_name="StockReturns.csv")
generate_returns(Bond_Mean, Bond_Stdev, Bond_Annual_High, Bond_Annual_Low, file_name="BondReturns.csv")
generate_returns(RE_Mean, RE_Stdev, RE_Annual_High, RE_Annual_Low, file_name="REReturns.csv")
