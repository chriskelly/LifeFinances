# Constants
import os, git, json
git_root= git.Repo(os.path.abspath(''),search_parent_directories=True).git.rev_parse('--show-toplevel')

PARAMS_LOC = os.path.join(git_root,'data/params.json')
DEFAULT_PARAMS_LOC = os.path.join(git_root,'data/default_params/params.json')
PARAMS_SUCCESS_LOC = os.path.join(git_root,'data/param_success.json')
QUIT_LOC = os.path.join(git_root,'cancel.quit')
SAVE_DIR = os.path.join(git_root,'diagnostics/saved')

EQUITY_MEAN = 1.092
"""Geometric average yield for stock invesments"""
EQUITY_STDEV = .16
"""Standard deviation of yield for stock invesments"""
EQUITY_ANNUAL_HIGH = 1.121 
"""Highest allowed annualized lifetime yield for stock investments,
based on historical data of rolling time periods"""
EQUITY_ANNUAL_LOW = 1.053
"""Lowest allowed annualized lifetime yield for stock investments,
based on historical data of rolling time periods"""

BOND_MEAN = 1.02
"""Geometric average yield for bond invesments"""
BOND_STDEV = .025
"""Standard deviation of yield for bond invesments"""
BOND_ANNUAL_HIGH = 1.02
"""Highest allowed annualized lifetime yield for bond investments,
based on historical data of rolling time periods"""
BOND_ANNUAL_LOW = 1.015
"""Lowest allowed annualized lifetime yield for bond investments,
based on historical data of rolling time periods"""

RE_MEAN = 1.11
"""Geometric average yield for real estate invesments"""
RE_STDEV = .14
"""Standard deviation of yield for real estate invesments"""
RE_ANNUAL_HIGH = 1.12
"""Highest allowed annualized lifetime yield for real estate investments,
based on estimated data of rolling time periods"""
RE_ANNUAL_LOW = 1.08
"""Lowest allowed annualized lifetime yield for real estate investments,
based on estimated data of rolling time periods"""

INFLATION_MEAN = 1.037  # https://fred.stlouisfed.org/series/FPCPITOTLZGUSA#
"""Geometric average inflation yield"""
INFLATION_STDEV = .027
"""Standard deviation of inflation yield"""
INFLATION_ANNUAL_HIGH = 1.063
"""Highest allowed annualized inflation yield,
based on historical data of rolling time periods"""
INFLATION_ANNUAL_LOW = 1.020
"""Lowest allowed annualized inflation yield,
based on historical data of rolling time periods"""
INFLATION_SKEW = 1.642
"""Historic skew of inflation yield"""

PENSION_INFLATION = 1.03 
"""Expected increase yield to Social Security and Pension figures"""

SS_MAX_EARNINGS = [ 
    [2002,84.900],
    [2003,87.000],
    [2004,87.900],
    [2005,90.000],
    [2006,94.200],
    [2007,97.500],
    [2008,102.000],
    [2009,106.800],
    [2010,106.800],
    [2011,106.800],
    [2012,110.100],
    [2013,113.700],
    [2014,117.000],
    [2015,118.500],
    [2016,118.500],
    [2017,127.200],
    [2018,128.400],
    [2019,132.900],
    [2020,137.700],
    [2021,142.800],
]
"""List of historic data in format: [year,social security max earnings]"""
SS_INDEXES = [ 
    [2002,1.7665978],
    [2003,1.7244432],
    [2004,1.6478390],
    [2005,1.5896724],
    [2006,1.5198170],
    [2007,1.4538392],
    [2008,1.4211470],
    [2009,1.4429071],
    [2010,1.4095913],
    [2011,1.3667660],
    [2012,1.3253803],
    [2013,1.3086540],
    [2014,1.2637941],
    [2015,1.2213044],
    [2016,1.2076578],
    [2017,1.1673463],
    [2018,1.1265158],
    [2019,1.0858240],
    [2020,1.0559868],
    [2021,1.0000000]
 ]
"""List of historic data in format: [year,social security indicies]"""
SS_BEND_POINTS=[1.024,6.172]
"""Bend points in $1000s in format: [low bend point, high bend point]"""
PIA_RATES=[0.9,0.32,0.15]
"""PIA rates in format: [rate below low bend point, rate between bend points,
rate above high bend point]"""
PIA_RATES_PENSION=[0.4,0.32,0.15]
"""Same as PIA rates, but the rate below the low bend point is 40% instead of 90%"""
BENEFIT_RATES= {
    "62":0.7,
    "63":0.75,
    "64":0.8,
    "65":0.867,
    "66":0.933,
    "67":1,
    "68":1.08,
    "69":1.16,
    "70":1.24
}
"""Dictionary of {age:benefit rate}. Benefit rate generally rises the longer you wait to pull SS """
FED_STD_DEDUCTION=	 [12.950, 25.900]
"""2022 federal standard deduction"""
FED_BRACKET_RATES= [
    [
        [0.1, 10.275, 0],
        [0.12, 41.775, 1.027],  
        [0.22, 89.075, 4.807],
        [0.24, 170.050, 15.213], 
        [0.32, 215.950, 34.647], 
        [0.35, 539.900, 49.335],
        [0.37, float('inf'), 162.718]  
    ],
    [
        [0.1, 20.500, 0],
        [0.12, 83.550, 2.05],  
        [0.22, 178.150, 9.616],
        [0.24, 340.100, 30.428], 
        [0.32, 431.900, 69.296], 
        [0.35, 647.850, 98.672],
        [0.37, float('inf'), 174.254]  
    ]
    ]
"""2022 federal brackets for income tax in format [rate,highest dollar that rate applies to,sum of tax owed in previous brackets]"""

""" Code to calc third column of bracket rates
from data import constants as const
brackets_set = const.FED_BRACKET_RATES
rate_idx, cap_idx = 0, 1
for brackets in brackets_set:
    res = [0,brackets[0][rate_idx] * brackets[0][cap_idx]] # first 2
    for i in range(1,len(brackets)-1):
        res.append(res[-1] + brackets[i][rate_idx]*(brackets[i][cap_idx]-brackets[i-1][cap_idx]))
    print(res)
"""

STATE_STD_DEDUCTION= [4.803, 9.606]
"""2022 california standard deduction"""
STATE_BRACKET_RATES= [
    [
        [0.01, 9.325, 0],
        [0.02, 22.107, 0.093],  
        [0.04, 34.892, 0.348],
        [0.06, 48.435, 0.860], 
        [0.08, 61.214, 1.672], 
        [0.093, 312.686, 2.695],
        [0.103, 375.221, 26.082],
        [0.113, 625.369, 32.523],
        [0.123, float('inf'), 60.789]
    ],
    [
        [0.01, 18.649, 0],
        [0.02, 44.213, 0.186],  
        [0.04, 69.783, 0.698],
        [0.06, 96.869, 1.720], 
        [0.08, 122.427, 3.346], 
        [0.093, 625.371, 5.390],
        [0.103, 750.442, 52.164],
        [0.113, 1250.738, 65.046],
        [0.123, float('inf'), 121.580]
    ]
]
"""2022 CA brackets for income tax in format [rate,highest dollar that rate applies to,sum of tax owed in previous brackets]"""

ANNUITY_INT_YIELD = 1.05 
"""Interest yield on annuity (Fidelity used as benchmark). https://digital.fidelity.com/prgw/digital/gie/"""
ANNUITY_PAYOUT_RATE = 0.045
"""Payout rate on annuity (Fidelity used as benchmark). https://digital.fidelity.com/prgw/digital/gie/"""

# Admin's pension details, ignore!
ADMIN_PENSION_RATES={
    "2043": .0116,
    "2044": .0128,
    "2045": .0140,
    "2046": .0152,
    "2047": .0164,
    "2048": .0176,
    "2049": .0188,
    "2050": .0200,
    "2051": .0213,
    "2052": .0227,
    "2053": .0240,
    "2054": .0240,
    "2055": .0240
}
"""Please ignore. Pension details for admin. Format: {year:rate}"""
PENSION_ACCOUNT_BAL = 56.307 # lastpass 'pension bal'
"""Please ignore. Pension details for admin."""
PENSION_COST = 0.09 # 9% of income
"""Please ignore. Pension details for admin."""
PENSION_ACCOUNT_BAL_UP_DATE = 2022.5
"""Please ignore. Pension details for admin. Last date of update"""
PENSION_INTEREST_YIELD = 1.02 # varies from 1.2-3% based on Progress Reports
"""Please ignore. Pension details for admin."""
