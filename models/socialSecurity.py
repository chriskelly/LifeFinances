import math
import numpy as np
from data import constants as const
import simulator
from models import returnGenerator

SS_MAX_EARNINGS = np.transpose(np.array(const.SS_MAX_EARNINGS))
x_M_E, y_M_E = SS_MAX_EARNINGS[0], SS_MAX_EARNINGS[1]
fit_M_E = np.polyfit(x_M_E, np.log(y_M_E), 1)
a_M_E, b_M_E = np.exp(fit_M_E[1]), fit_M_E[0]
def est_Max_Earning(year):
    return a_M_E * np.exp(b_M_E * year)
SS_INDEXES = np.transpose(np.array(const.SS_INDEXES))
x_I, y_I = SS_INDEXES[0], SS_INDEXES[1]
fit_I = np.polyfit(x_I, np.log(y_I), 1)
a_I, b_I = np.exp(fit_I[1]), fit_I[0]
def est_Index(year):
    return a_I * np.exp(b_I * year)

WORK_START_AGE = 22 # Assumed age for starting work


class SSCalc:
    def __init__(self,simulator,current_age:int,FLAT_INFLATION,time_ls,income_ls,imported_record:dict={},eligible = True,pension_pia = False):
        self.age = current_age
        self.FLAT_INFLATION = FLAT_INFLATION
        self.simulator = simulator
        self.time_ls = time_ls
        self.earnings_record = {int(year):float(earning) for (year,earning) in imported_record.items()} # {year : earnings}
        if eligible: # if income is eligible to contribute to social security
            self._add_to_earnings_record(time_ls,income_ls)
            if imported_record == {}: self._back_estimate()
        # index and limit the earnings, then sort them from high to low
        ss_earnings = [min(est_Max_Earning(year),earning) * est_Index(year) 
                       for (year,earning) in self.earnings_record.items()]
        ss_earnings.sort(reverse=True)
        # Find Average Indexed Monthly Earnings (AIME), only top 35 years (420 months) count
        aime = sum(ss_earnings[:35])/420
        # Calculate monthly Primary Insurance Amounts (PIA) using bend points. Add AIME and sort to see where the AIME ranks in the bend points
        bend_points =const.SS_BEND_POINTS+[aime]
        bend_points.sort()
            # cut off bend points at inserted AIME
        bend_points = bend_points[:bend_points.index(aime)+1]
        # for the first bracket, just the bend times the rate. After that, find the marginal income to multiple by the rate
            # PIA rates are lower if you have certain pension incomes
        if pension_pia: pia_rates = const.PIA_RATES_PENSION
        else: pia_rates = const.PIA_RATES
        self.full_PIA = sum([(bend_points[i]-bend_points[i-1])*rate if i!=0 else bend*rate for (i,bend), rate 
                                in zip(enumerate(bend_points),pia_rates)])
        #TODO if no earnings given, estimate backward from age
    
    def ss_ls(self, date, inflation_ls):
        """return list with social security payments starting from first payment till final date"""
        ss_age = self.age + (math.trunc(date) - simulator.TODAY_YR)
        # convert to est. value at ss start-year and convert to quarterly (3 x monthly)
        pia = self.full_PIA * const.BENEFIT_RATES[str(ss_age)]
        ss_qt = 3 * pia / est_Index(date) # index factor is neutral to last update, so PIA is in that year's dollars and needs to be adjusted
        # build out list, add the correct number of zeros to the beginning, optimize later into list comprehension
        ss_ls = list(3 * pia * np.array(inflation_ls))
        idx = self.time_ls.index(date)
        ss_ls = [0]*idx + ss_ls[idx:]
        return ss_ls
        
    def _add_to_earnings_record(self,time_ls,income_ls):
        for date, income in zip(time_ls,income_ls):
            year = math.trunc(date)
            #TODO: Deal with fractional income years (the first year typically only gets a fraction of the actual income for that year)
            if income != 0:
                if year in self.earnings_record:
                    self.earnings_record[year] += income
                else: self.earnings_record[year] = income
    
    
    def _back_estimate(self):
        pass # backfill assumed earnings
            
    
def test_unit():
    my_simulator = simulator.test_unit()
    test_time_ls = [2022.75, 2023.0, 2023.25, 2023.5, 2023.75, 2024.0, 2024.25, 2024.5, 2024.75, 2025.0, 2025.25, 2025.5, 2025.75, 2026.0, 2026.25, 2026.5, 2026.75, 2027.0, 2027.25, 2027.5, 2027.75, 2028.0, 2028.25, 2028.5, 2028.75, 2029.0, 2029.25, 2029.5, 2029.75, 2030.0, 2030.25, 2030.5, 2030.75, 2031.0, 2031.25, 2031.5, 2031.75, 2032.0, 2032.25, 2032.5, 2032.75, 2033.0, 2033.25, 2033.5, 2033.75, 2034.0, 2034.25, 2034.5, 2034.75, 2035.0, 2035.25, 2035.5, 2035.75, 2036.0, 2036.25, 2036.5, 2036.75, 2037.0, 2037.25, 2037.5, 2037.75, 2038.0, 2038.25, 2038.5, 2038.75, 2039.0, 2039.25, 2039.5, 2039.75, 2040.0, 2040.25, 2040.5, 2040.75, 2041.0, 2041.25, 2041.5, 2041.75, 2042.0, 2042.25, 2042.5, 2042.75, 2043.0, 2043.25, 2043.5, 2043.75, 2044.0, 2044.25, 2044.5, 2044.75, 2045.0, 2045.25, 2045.5, 2045.75, 2046.0, 2046.25, 2046.5, 2046.75, 2047.0, 2047.25, 2047.5, 2047.75, 2048.0, 2048.25, 2048.5, 2048.75, 2049.0, 2049.25, 2049.5, 2049.75, 2050.0, 2050.25, 2050.5, 2050.75, 2051.0, 2051.25, 2051.5, 2051.75, 2052.0, 2052.25, 2052.5, 2052.75, 2053.0, 2053.25, 2053.5, 2053.75, 2054.0, 2054.25, 2054.5, 2054.75, 2055.0, 2055.25, 2055.5, 2055.75, 2056.0, 2056.25, 2056.5, 2056.75, 2057.0, 2057.25, 2057.5, 2057.75, 2058.0, 2058.25, 2058.5, 2058.75, 2059.0, 2059.25, 2059.5, 2059.75, 2060.0, 2060.25, 2060.5, 2060.75, 2061.0, 2061.25, 2061.5, 2061.75, 2062.0, 2062.25, 2062.5, 2062.75, 2063.0, 2063.25, 2063.5, 2063.75, 2064.0, 2064.25, 2064.5, 2064.75, 2065.0, 2065.25, 2065.5, 2065.75, 2066.0, 2066.25, 2066.5, 2066.75, 2067.0, 2067.25, 2067.5, 2067.75, 2068.0, 2068.25, 2068.5, 2068.75, 2069.0, 2069.25, 2069.5, 2069.75, 2070.0, 2070.25, 2070.5, 2070.75, 2071.0, 2071.25, 2071.5, 2071.75, 2072.0, 2072.25, 2072.5, 2072.75, 2073.0, 2073.25, 2073.5, 2073.75, 2074.0, 2074.25, 2074.5, 2074.75, 2075.0, 2075.25, 2075.5, 2075.75, 2076.0, 2076.25, 2076.5, 2076.75, 2077.0, 2077.25, 2077.5, 2077.75, 2078.0, 2078.25, 2078.5, 2078.75, 2079.0, 2079.25, 2079.5, 2079.75, 2080.0, 2080.25, 2080.5, 2080.75, 2081.0, 2081.25, 2081.5, 2081.75, 2082.0, 2082.25, 2082.5, 2082.75, 2083.0, 2083.25, 2083.5, 2083.75, 2084.0, 2084.25, 2084.5, 2084.75, 2085.0, 2085.25, 2085.5, 2085.75, 2086.0, 2086.25, 2086.5, 2086.75, 2087.0, 2087.25, 2087.5, 2087.75, 2088.0, 2088.25, 2088.5, 2088.75, 2089.0, 2089.25, 2089.5, 2089.75]
    test_income_ls = [75.48375, 78.5031, 78.5031, 78.5031, 78.5031, 81.643224, 81.643224, 81.643224, 81.643224, 84.90895296000001, 84.90895296000001, 84.90895296000001, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    test_user_record = {
            "2002":"1.007",
            "2003":"1.192",
            "2009":"9.387",
            "2010":"19.489",
            "2011":"35.725",
            "2012":"40.728",
            "2013":"38.485",
            "2014":"31.144",
            "2015":"51.986",
            "2016":"36.440",
            "2018":"0.635"
        }
    ss_calc =  SSCalc(my_simulator,current_age=29,FLAT_INFLATION=1.03,
                     time_ls=test_time_ls,income_ls=test_income_ls,
                     imported_record=test_user_record)
    inflation_ls = returnGenerator.main(my_simulator.rows,4,1)[3][0]
    return ss_calc.ss_ls(date=2061.25,inflation_ls=inflation_ls)