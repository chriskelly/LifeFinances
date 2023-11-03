"""Utililty Functions"""

import math

import numpy as np
from app.data import constants


def constrain(value, low=float("-inf"), high=float("inf")):
    """Constrain the output of a value between an upper and lower limit.

    Args:
        value (int/float)
        low (int/float): Defaults to negative infinity
        high (int/float): Defaults to positive infinity

    Returns:
        int/float: The value clamped between the limits.
    """
    if value < low:
        return low
    if value > high:
        return high
    return value


def interval_yield(yield_value: float) -> float:
    """Turn an annual yield into a yield for an interval

    Args:
        yield_value (float): an annual yield in the format of 1.03

    Returns:
        float: interval yield
    """
    return yield_value**constants.YEARS_PER_INTERVAL


def interval_stdev(stdev: float) -> float:
    """Turn an annual standard deviation into an interval standard deviation

    Args:
        stdev (float): an annual standard deviation in the format of 0.15

    Returns:
        float: interval standard deviation
    """
    return stdev * math.sqrt(constants.YEARS_PER_INTERVAL)


def exponential_extrapolator_factory(data_list: list[list]) -> callable:
    """Factory for creating exponential extrapolators

    Args:
        data_list (list[list[float,float]]): list of lists of the form [x, y]

    Returns:
        callable: extrapolator function
    """
    x_array, y_array = np.transpose(np.array(data_list))
    fit = np.polyfit(x=x_array, y=np.log(y_array), deg=1)
    intercept = np.exp(fit[1])
    slope = fit[0]

    def extrapolator(date: float) -> float:
        """Return estimated value for date based on exponential fit.

        Args:
            date (float): date to estimate value for

        Returns:
            float: estimated value
        """
        return intercept * np.exp(slope * date)

    return extrapolator


index_extrapolator = exponential_extrapolator_factory(constants.SS_INDEXES)
max_earnings_extrapolator = exponential_extrapolator_factory(constants.SS_MAX_EARNINGS)
