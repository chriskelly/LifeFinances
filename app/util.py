"""Utililty Functions"""

from abc import ABC, abstractmethod
import math

import numpy as np
from app.data import constants


class FloatRepr(ABC):
    """Abstract class for representing a class as a float

    Provides functionality to allow a class to be represented
    as a float and for mathematical operations to be performed on it.

    Must have `def __float__(self)` method

    Example usage:

    ```
    class TotalBill:
        def __init__(self, subtotal, tax):
            self.subtotal = subtotal
            self.tax = tax

        def __float__(self):
            return self.subtotal + self.tax

    my_total_bill = TotalBill(subtotal=21.34, tax=1.78)

    my_total_bill / 3 # returns 7.71, rather than TypeError
    ```
    """

    @abstractmethod
    def __float__(self):
        pass

    def __repr__(self):
        return str(float(self))

    def __str__(self):
        return str(float(self))

    def __add__(self, value):
        return float(self) + value

    def __radd__(self, value):
        return value + float(self)

    def __sub__(self, value):
        return float(self) - value

    def __rsub__(self, value):
        return value - float(self)

    def __mul__(self, value):
        return float(self) * value

    def __rmul__(self, value):
        return value * float(self)

    def __truediv__(self, value):
        return float(self) / value

    def __rtruediv__(self, value):
        return value / float(self)

    def __floordiv__(self, value):
        return float(self) // value

    def __rfloordiv__(self, value):
        return value // float(self)

    def __mod__(self, value):
        return float(self) % value

    def __rmod__(self, value):
        return value % float(self)

    def __pow__(self, value):
        return float(self) ** value

    def __rpow__(self, value):
        return value ** float(self)


class IntRepr(ABC):
    """Abstract class for representing a class as an int

    Provides functionality to allow a class to be represented
    as an int and for mathematical operations to be performed on it.

    Must have `def __int__(self)` method

    Example usage:

    ```
    class PetCount:
        def __init__(self, cats, cogs):
            self.cats = cats
            self.dogs = dogs

        def __int__(self):
            return self.cats + self.dogs

    my_pet_count = PetCount(cats=2, dogs=4)

    5 + my_pet_count # returns 11, rather than TypeError
    ```
    """

    @abstractmethod
    def __int__(self):
        pass

    def __repr__(self):
        return str(int(self))

    def __str__(self):
        return str(int(self))

    def __add__(self, value):
        return int(self) + value

    def __radd__(self, value):
        return self.__add__(value)

    def __sub__(self, value):
        return int(self) - value

    def __rsub__(self, value):
        return value - int(self)

    def __mul__(self, value):
        return int(self) * value

    def __rmul__(self, value):
        return value * int(self)

    def __truediv__(self, value):
        return int(self) / value

    def __rtruediv__(self, value):
        return value / int(self)

    def __floordiv__(self, value):
        return int(self) // value

    def __rfloordiv__(self, value):
        return value // int(self)

    def __mod__(self, value):
        return int(self) % value

    def __rmod__(self, value):
        return value % int(self)

    def __pow__(self, value):
        return int(self) ** value

    def __rpow__(self, value):
        return value ** int(self)


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
