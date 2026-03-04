"""Tax Rates and Functions

This module contains the constants related to taxes across all supported states.

"""

# Use `taxes.ipynb` to generate the third column of the bracket rates

FED_STD_DEDUCTION = [15.000, 30.000]
"""2025 federal standard deduction"""
FED_BRACKET_RATES = [
    [
        [0.1, 11.925, 0],
        [0.12, 48.475, 1.193],
        [0.22, 103.350, 5.579],
        [0.24, 197.300, 17.651],
        [0.32, 250.525, 40.199],
        [0.35, 626.350, 57.231],
        [0.37, float("inf"), 188.77],
    ],
    [
        [0.1, 23.85, 0],
        [0.12, 96.95, 2.385],
        [0.22, 206.7, 11.157],
        [0.24, 394.6, 35.302],
        [0.32, 501.05, 80.398],
        [0.35, 751.6, 114.462],
        [0.37, float("inf"), 202.154],
    ],
]
"""2022 federal brackets for income tax in format
[rate,highest dollar that rate applies to,sum of tax owed in previous brackets]"""

STATE_STD_DEDUCTION = {
    "California": [5.540, 11.080],  # 2025
    "New York": [8.000, 16.050],  # 2022
}
"""State standard deduction. state:[single, married]"""
STATE_BRACKET_RATES = {
    "California": [  # 2025
        [
            [0.01, 10.756, 0],
            [0.02, 25.499, 0.108],
            [0.04, 40.245, 0.403],
            [0.06, 55.866, 0.993],
            [0.08, 70.606, 1.93],
            [0.093, 360.659, 3.109],
            [0.103, 432.787, 30.084],
            [0.113, 721.314, 37.513],
            [0.123, float("inf"), 70.117],
        ],
        [
            [0.01, 21.512, 0],
            [0.02, 50.998, 0.215],
            [0.04, 80.49, 0.805],
            [0.06, 111.732, 1.985],
            [0.08, 141.212, 3.86],
            [0.093, 721.318, 6.218],
            [0.103, 865.574, 60.168],
            [0.113, 1442.628, 75.026],
            [0.123, float("inf"), 140.233],
        ],
    ],
    "New York": [  # 2022
        [
            [0.04, 8.501, 0],
            [0.045, 11.701, 0.34],
            [0.0525, 13.901, 0.484],
            [0.0585, 80.651, 0.599],
            [0.0625, 215.401, 4.504],
            [0.0685, 1077.551, 12.926],
            [0.0965, 5000.001, 71.983],
            [0.103, 25000.001, 450.499],
            [0.109, float("inf"), 2510.499],
        ],
        [
            [0.04, 17.151, 0],
            [0.045, 23.601, 0.686],
            [0.0525, 27.901, 0.976],
            [0.0585, 161.551, 1.202],
            [0.0625, 323.201, 9.021],
            [0.0685, 2155.351, 19.124],
            [0.0965, 5000.001, 144.626],
            [0.103, 25000.001, 419.135],
            [0.109, float("inf"), 2479.135],
        ],
    ],
}
"""State brackets for income tax in format {state:[single brackets, married brackets]}.\n
Brackets in format [rate,highest dollar that rate applies to,
sum of tax owed in previous brackets]"""

MEDICARE_TAX_RATE = 0.0145
SOCIAL_SECURITY_TAX_RATE = 0.062
DISCOUNT_ON_PENSION_TAX = 0.2
