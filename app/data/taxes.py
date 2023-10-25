"""Tax Rates and Functions

This module contains the constants related to taxes across all supported states.

"""

FED_STD_DEDUCTION = [12.950, 25.900]
"""2022 federal standard deduction"""
FED_BRACKET_RATES = [
    [
        [0.1, 10.275, 0],
        [0.12, 41.775, 1.027],
        [0.22, 89.075, 4.807],
        [0.24, 170.050, 15.213],
        [0.32, 215.950, 34.647],
        [0.35, 539.900, 49.335],
        [0.37, float("inf"), 162.718],
    ],
    [
        [0.1, 20.500, 0],
        [0.12, 83.550, 2.05],
        [0.22, 178.150, 9.616],
        [0.24, 340.100, 30.428],
        [0.32, 431.900, 69.296],
        [0.35, 647.850, 98.672],
        [0.37, float("inf"), 174.254],
    ],
]
"""2022 federal brackets for income tax in format
[rate,highest dollar that rate applies to,sum of tax owed in previous brackets]"""

# Code to calc third column of bracket rates
# from data import taxes
# brackets_set = taxes.STATE_BRACKET_RATES['New York']
# rate_idx, cap_idx = 0, 1
# for brackets in brackets_set:
#     res = [0,round(brackets[0][rate_idx] * brackets[0][cap_idx], 3)] # first 2
#     for i in range(1,len(brackets)-1):
#         res.append(round(res[-1] + brackets[i][rate_idx]*(brackets[i][cap_idx]
#                                                           -brackets[i-1][cap_idx]), 3))
#     for i in range(len(res)-1):
#         print(f'{[brackets[i][rate_idx], brackets[i][cap_idx], res[i]]},')
#     print(f"[{brackets[-1][rate_idx]}, float('inf'), {res[-1]}]")

STATE_STD_DEDUCTION = {
    "California": [4.803, 9.606],  # 2022
    "New York": [8.000, 16.050],  # 2022
}
"""State standard deduction. state:[single, married]"""
STATE_BRACKET_RATES = {
    "California": [  # 2022
        [
            [0.01, 9.325, 0],
            [0.02, 22.107, 0.093],
            [0.04, 34.892, 0.348],
            [0.06, 48.435, 0.860],
            [0.08, 61.214, 1.672],
            [0.093, 312.686, 2.695],
            [0.103, 375.221, 26.082],
            [0.113, 625.369, 32.523],
            [0.123, float("inf"), 60.789],
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
            [0.123, float("inf"), 121.580],
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
