import simulator

class Income:
    def __init__(self,income_obj:dict,previous_income):
        self.previous_income:Income = previous_income
        self.income_qt = income_obj['Starting Income'] / 4
        self.tax_deferred_qt = income_obj['Tax Deferred Income'] / 4
        self.duration_qt = int(income_obj['Duration'] * 4)
        self.yearly_raise = income_obj['Yearly Raise'] + 1 # needs to be in yield format
        self.reduction_target:bool = income_obj['Try to Reduce'] # genetic.Algorithm will try to reduce the duration of this income stream
        
    def start_date(self) -> int:
        """Returns the index for the date_ls"""
        if not self.previous_income:
            return 0
        else:
            return self.previous_income.end_date() + 1
        
    def end_date(self) -> int:
        """Returns the index for the date_ls"""
        return self.start_date() + self.duration_qt - 1
        
def generate_lists(income_dicts:list[dict],date_ls:list)-> tuple[list, list]:
    """Return one combined list of all incomes and no-income dates

    Args:
        income_dicts (list[dict]): list obtained from params
        date_ls (list)

    Returns:
        list
    """
    income_objs = [Income(income_dicts[0],previous_income=None)]
    for i in range(1,len(income_dicts)):
        income_objs.append(Income(income_dicts[i],previous_income=income_objs[-1]))
    income_ls, deferred_ls =[], []
    for income in income_objs:
        income_ls += simulator.step_quarterize2(date_ls,first_val=income.income_qt,increase_yield=income.yearly_raise,
                                             start_date_idx=income.start_date(),end_date_idx=income.end_date())
        deferred_ls += simulator.step_quarterize2(date_ls,first_val=income.tax_deferred_qt,increase_yield=income.yearly_raise,
                                             start_date_idx=income.start_date(),end_date_idx=income.end_date())
    income_ls += [0]*(len(date_ls)-len(income_ls))
    deferred_ls += [0]*(len(date_ls)-len(deferred_ls))
    return income_ls, deferred_ls


"""Testing Script
import models.income
incomes = [
    {
        'Starting Income':180000,
        'Duration':3.5,
        'Yearly Raise':0.04,
        'Try to Reduce':False
    },
    {
        'Starting Income':120000,
        'Duration':2,
        'Yearly Raise':0.06,
        'Try to Reduce':True
    },
    {
        'Starting Income':50000,
        'Duration':4,
        'Yearly Raise':0.02,
        'Try to Reduce':False
    },
]
date_ls = [2022.75, 2023.0, 2023.25, 2023.5, 2023.75, 2024.0, 2024.25, 2024.5, 2024.75, 2025.0, 2025.25, 2025.5, 2025.75, 2026.0, 2026.25, 2026.5, 2026.75, 2027.0, 2027.25, 2027.5, 2027.75, 2028.0, 2028.25, 2028.5, 2028.75, 2029.0, 2029.25, 2029.5, 2029.75, 2030.0, 2030.25, 2030.5, 2030.75, 2031.0, 2031.25, 2031.5, 2031.75, 2032.0, 2032.25, 2032.5, 2032.75, 2033.0, 2033.25, 2033.5, 2033.75, 2034.0, 2034.25, 2034.5, 2034.75, 2035.0, 2035.25, 2035.5, 2035.75, 2036.0, 2036.25, 2036.5, 2036.75, 2037.0, 2037.25, 2037.5, 2037.75, 2038.0, 2038.25, 2038.5, 2038.75, 2039.0, 2039.25, 2039.5, 2039.75, 2040.0, 2040.25, 2040.5, 2040.75, 2041.0, 2041.25, 2041.5, 2041.75, 2042.0, 2042.25, 2042.5, 2042.75, 2043.0, 2043.25, 2043.5, 2043.75, 2044.0, 2044.25, 2044.5, 2044.75, 2045.0, 2045.25, 2045.5, 2045.75, 2046.0, 2046.25, 2046.5, 2046.75, 2047.0, 2047.25, 2047.5, 2047.75, 2048.0, 2048.25, 2048.5, 2048.75, 2049.0, 2049.25, 2049.5, 2049.75, 2050.0, 2050.25, 2050.5, 2050.75, 2051.0, 2051.25, 2051.5, 2051.75, 2052.0, 2052.25, 2052.5, 2052.75, 2053.0, 2053.25, 2053.5, 2053.75, 2054.0, 2054.25, 2054.5, 2054.75, 2055.0, 2055.25, 2055.5, 2055.75, 2056.0, 2056.25, 2056.5, 2056.75, 2057.0, 2057.25, 2057.5, 2057.75, 2058.0, 2058.25, 2058.5, 2058.75, 2059.0, 2059.25, 2059.5, 2059.75, 2060.0, 2060.25, 2060.5, 2060.75, 2061.0, 2061.25, 2061.5, 2061.75, 2062.0, 2062.25, 2062.5, 2062.75, 2063.0, 2063.25, 2063.5, 2063.75, 2064.0, 2064.25, 2064.5, 2064.75, 2065.0, 2065.25, 2065.5, 2065.75, 2066.0, 2066.25, 2066.5, 2066.75, 2067.0, 2067.25, 2067.5, 2067.75, 2068.0, 2068.25, 2068.5, 2068.75, 2069.0, 2069.25, 2069.5, 2069.75, 2070.0, 2070.25, 2070.5, 2070.75, 2071.0, 2071.25, 2071.5, 2071.75, 2072.0, 2072.25, 2072.5, 2072.75, 2073.0, 2073.25, 2073.5, 2073.75, 2074.0, 2074.25, 2074.5, 2074.75, 2075.0, 2075.25, 2075.5, 2075.75, 2076.0, 2076.25, 2076.5, 2076.75, 2077.0, 2077.25, 2077.5, 2077.75, 2078.0, 2078.25, 2078.5, 2078.75, 2079.0, 2079.25, 2079.5, 2079.75, 2080.0, 2080.25, 2080.5, 2080.75, 2081.0, 2081.25, 2081.5, 2081.75, 2082.0, 2082.25, 2082.5, 2082.75, 2083.0, 2083.25, 2083.5, 2083.75, 2084.0, 2084.25, 2084.5, 2084.75, 2085.0, 2085.25, 2085.5, 2085.75, 2086.0, 2086.25, 2086.5, 2086.75, 2087.0, 2087.25, 2087.5, 2087.75, 2088.0, 2088.25, 2088.5, 2088.75, 2089.0, 2089.25, 2089.5, 2089.75]
income_ls = models.income.generate_income_ls(incomes,date_ls)
"""