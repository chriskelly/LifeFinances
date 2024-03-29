"""Constants for Retirement Planning Simulator

This module contains the constants used across multiple modules in
the Life Finances package

"""
import datetime as dt
from pathlib import Path

CONFIG_PATH = Path("config.yml")
SAMPLE_FULL_CONFIG_PATH = Path("tests/sample_configs/full_config.yml")
SAMPLE_MIN_CONFIG_INCOME_PATH = Path("tests/sample_configs/min_config_income.yml")
SAMPLE_MIN_CONFIG_NET_WORTH_PATH = Path("tests/sample_configs/min_config_net_worth.yml")
CORRELATION_PATH = Path("app/data/variable_correlation.csv")
STATISTICS_PATH = Path("app/data/variable_statistics.csv")
PARAMS_SUCCESS_LOC = Path("data/param_success.json")
QUIT_LOC = Path("cancel.quit")
SAVE_DIR = Path("diagnostics/saved")

TODAY = dt.date.today()
TODAY_QUARTER = (TODAY.month - 1) // 3
TODAY_YR = TODAY.year
TODAY_YR_QT = TODAY.year + TODAY_QUARTER * 0.25

INTERVALS_PER_YEAR = 4
YEARS_PER_INTERVAL = 1 / INTERVALS_PER_YEAR
MONTHS_PER_INTERVAL = round(12 / INTERVALS_PER_YEAR)

PENSION_INFLATION = 1.03
"""Expected increase yield to Social Security and Pension figures"""

SS_MAX_EARNINGS = [
    [2002, 84.900],
    [2003, 87.000],
    [2004, 87.900],
    [2005, 90.000],
    [2006, 94.200],
    [2007, 97.500],
    [2008, 102.000],
    [2009, 106.800],
    [2010, 106.800],
    [2011, 106.800],
    [2012, 110.100],
    [2013, 113.700],
    [2014, 117.000],
    [2015, 118.500],
    [2016, 118.500],
    [2017, 127.200],
    [2018, 128.400],
    [2019, 132.900],
    [2020, 137.700],
    [2021, 142.800],
]
"""List of historic data in format: [year,social security max earnings]"""
SS_INDEXES = [
    [2002, 1.7665978],
    [2003, 1.7244432],
    [2004, 1.6478390],
    [2005, 1.5896724],
    [2006, 1.5198170],
    [2007, 1.4538392],
    [2008, 1.4211470],
    [2009, 1.4429071],
    [2010, 1.4095913],
    [2011, 1.3667660],
    [2012, 1.3253803],
    [2013, 1.3086540],
    [2014, 1.2637941],
    [2015, 1.2213044],
    [2016, 1.2076578],
    [2017, 1.1673463],
    [2018, 1.1265158],
    [2019, 1.0858240],
    [2020, 1.0559868],
    [2021, 1.0000000],
]
"""List of historic data in format: [year,social security indicies]"""
SS_BEND_POINTS = [1.024, 6.172]
"""Bend points in $1000s in format: [low bend point, high bend point]"""
PIA_RATES = [0.9, 0.32, 0.15]
"""PIA rates in format: [rate below low bend point, rate between bend points,
rate above high bend point]"""
PIA_RATES_PENSION = [0.4, 0.32, 0.15]
"""Same as PIA rates, but the rate below the low bend point is 40% instead of 90%"""
BENEFIT_RATES = {
    62: 0.7,
    63: 0.75,
    64: 0.8,
    65: 0.867,
    66: 0.933,
    67: 1,
    68: 1.08,
    69: 1.16,
    70: 1.24,
}
"""Dictionary of {age:benefit rate}. Benefit rate generally rises the longer you wait to pull SS """

ANNUITY_INT_YIELD = 1.05
"""Interest yield on annuity (Fidelity used as benchmark).
https://digital.fidelity.com/prgw/digital/gie/"""
ANNUITY_PAYOUT_RATE = 0.045
"""Payout rate on annuity (Fidelity used as benchmark).
https://digital.fidelity.com/prgw/digital/gie/"""
