# download data from http://www.econ.yale.edu/~shiller/data.htm
# copy first 3 columns from data tab
# remove first 7 rows and last rows (including emptry rows, which is easier after csv file added to project)
# "Monthly dividend data is computed from the S&P four-quarter totals for the quarter since 1926, with linear interpolation to monthly figures."
    # so each value is 12 times the actual monthly amount. If you filter out to just one row per year though, you'd have an accurate dividend to use.

import pandas as pd

df = pd.read_csv('SP500_month_P_D.csv')
yearly_df = df[df['Date'].astype(str).str.contains('.01',regex=False)]
yearly_df.to_csv('SP500_year_P_D.csv')

# Total Return: =(C3+D2)/C2
# Annualized 40 years: =PRODUCT(E3:E42)^(1/40)
# Avg: =AVERAGE($F$3:$F$114)
# Max: =MAX($F$3:$F$114)
# Min: =MIN($F$3:$F$114)
