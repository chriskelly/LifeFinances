"""Model of stream of income for a given time

Required installations are detailed in requirements.txt.

"""

import numpy as np
import simulator
from models.user import JobIncome

class Income:
    """An object to represent an income stream.
    
    Attributes
    ----------
    previous_income : Income
        Income objects act as linked nodes that link to the previous income
    income_qt : float
        Starting quarterly income
    tax_deferred_qt : float
        Starting quarterly tax deferred income
    last_date_idx : int
        Index of the last date in the date_ls
    yearly_raise : float
        Yearly raise in yield format
    optimization_target : bool
        If true, genetic.Algorithm will try to reduce the duration of this income stream
    ss_eligible : bool
        Is this income subject to social security tax?
    income_ls : list[float]
        The income mapped for each date, increasing by the raise amount each year
    deferred_ls : list[float]
        The tax deferred income mapped for each date, increasing by the raise amount each year
    
    Methods
    -------
    start_date_idx()
        Returns the index for the date_ls that the income begins
    """
    def __init__(self, income_profile:JobIncome, date_ls:list, previous_income):
        self.previous_income:Income = previous_income
        self.income_qt:float = income_profile.starting_income / 4
        self.tax_deferred_qt = income_profile.tax_deferred_income / 4
        self.last_date_idx = date_ls.index(income_profile.last_date)
        self.yearly_raise:float = income_profile.yearly_raise + 1 # needs to be in yield format
        self.optimization_target:bool = bool(income_profile.try_to_optimize)
        self.ss_eligible:bool = bool(income_profile.social_security_eligible)
        self.income_ls = simulator.step_quarterize(date_ls, first_val=self.income_qt,
                                                   increase_yield=self.yearly_raise,
                                                    start_date_idx=self.start_date_idx(),
                                                    end_date_idx=self.last_date_idx)
        self.deferred_ls = simulator.step_quarterize(date_ls, first_val=self.tax_deferred_qt,
                                                     increase_yield=self.yearly_raise,
                                                    start_date_idx=self.start_date_idx(),
                                                    end_date_idx=self.last_date_idx)

    def start_date_idx(self) -> int:
        """Returns the index for the date_ls"""
        if not self.previous_income:
            return 0
        return self.previous_income.last_date_idx + 1

class IncomeGroup:
    """A collection of Incomes.
    
    Attributes
    ----------
    income_objs : list[Income]
        A sequential list of Income objects
    total_income_ls : list[float]
        The total income mapped for each date, increasing by the raise amount each year
    total_deferred_ls : list[float]
        The total tax deferred income mapped for each date, increasing by the raise amount each year
    """
    def __init__(self, income_profiles:list[JobIncome], date_ls:list):
        # Make list of Income objects
        self.profiles = [Income(income_profiles[0], date_ls, previous_income=None)]
        for i in range(1,len(income_profiles)):
            self.profiles.append(Income(income_profiles[i], date_ls,
                                           previous_income=self.profiles[-1]))
        # Make lists of total income & tax-deferred income
        self.total_income_ls, self.total_deferred_ls =[], []
        for income in self.profiles:
            self.total_income_ls += income.income_ls
            self.total_deferred_ls += income.deferred_ls
        self.total_income_ls += [0]*(len(date_ls)-len(self.total_income_ls))
        self.total_deferred_ls += [0]*(len(date_ls)-len(self.total_deferred_ls))

def generate_lists(user_income_group:IncomeGroup, partner_income_group:IncomeGroup = None)\
    -> tuple[list, list]:
    """Returns one combined list of all incomes and one list of tax-deferred income.
    \n Given list of Calculators, add them together and return sum

    Args:
        user_calc (income.Calculator)
        partner_calc (income.Calculator): optional

    Returns:
        tuple[list, list]
    """
    if partner_income_group:
        income_ls = list(np.array(user_income_group.total_income_ls)
                         +np.array(partner_income_group.total_income_ls))
        deferred_ls = list(np.array(user_income_group.total_deferred_ls)\
                        +np.array(partner_income_group.total_deferred_ls))
    else:
        income_ls = user_income_group.total_income_ls
        deferred_ls = user_income_group.total_deferred_ls
    return income_ls, deferred_ls
