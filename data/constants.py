# Constants

PARAMS_LOC = 'data/params.json'
PARAMS_SUCCESS_LOC = 'data/param_success.json'

EQUITY_MEAN = 1.092
EQUITY_STDEV = .16
EQUITY_ANNUAL_HIGH = 1.121 
EQUITY_ANNUAL_LOW = 1.053

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

SS_BEND_POINTS=[1.024,6.172]
HIS_PIA_RATES=[0.9,0.32,0.15]
HER_PIA_RATES=[0.4,0.32,0.15]
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
FED_STD_DEDUCTION=	 25.900
FED_BRACKET_RATES= [
    [0.1, 20.500],
    [0.12, 83.550],  
    [0.22, 178.150],
    [0.24, 340.100], 
    [0.32, 431.900], 
    [0.35, 647.850]  
]
CA_STD_DEDUCTION= 9.606
CA_BRACKET_RATES= [
    [0.01, 18.649],
    [0.02, 44.213],  
    [0.04, 69.783],
    [0.06, 96.869], 
    [0.08, 122.427], 
    [0.093, 625.371]
]
DENICA_PENSION_RATES={
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
PENSION_ACCOUNT_BAL = 56.307 # https://my.calstrs.com/
PENSION_COST = 0.09 # 9% of income
PENSION_ACCOUNT_BAL_UP_DATE = 2022.5
PENSION_INTEREST_YIELD = 1.02 # varies from 1.2-3% based on Progress Reports

ANNUITY_INT_YIELD = 1.05 # https://digital.fidelity.com/prgw/digital/gie/
ANNUITY_PAYOUT_RATE = 0.045