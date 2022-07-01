
"""
    First we're making a frame for the data. The frame will only be made once for each set of params (genes)
        Even though it's only made once per params, due to the hyper-volume we'll be testing, still needs to be fast
    Only necessary data is taken from the frame (or maybe the frame is only made of necessary data)
    Monte Carlo is run on the necessary frame to get success rate
    
"""
import datetime as dt
import json
import math
import numpy as np
import pandas as pd

TODAY = dt.date.today()
TODAY_QUARTER = (TODAY.month-1)//3
TODAY_YR = TODAY.year
TODAY_YR_QT = TODAY_YR+TODAY_QUARTER*.25
FLAT_INFLATION = 1.03 # Used for some estimations like pension
with open("params_gov.json") as json_file:
            gov_params = json.load(json_file)

class Simulator:
    def __init__(self,param_vals):
        self.params = self._clean_data(param_vals)
        self.rows = int((param_vals['Calculate Til'] - TODAY_YR_QT)/.25)
        self.fi_date = self.params["FI Quarter"]
            
    def main(self):
# -------------------------------- VARIABLES -------------------------------- #

    # values that are fixed regardless
        # Year.Quarter list
        time_ls = self._range_len(START=TODAY_YR_QT,LEN=self.rows,INCREMENT=0.25,ADD=True)
        
        # Are you FI list (1 = yes, 0 = no)
        working_qts = int((self.fi_date-TODAY_YR_QT)/.25)
        FI_qts = self.rows-working_qts
        FI_state_ls = [0]*working_qts +[1]*FI_qts
        
        # Job Income and tax-differed list. Does not include SS/Pensions. 
            # get quarterly income for his and her
        his_qt_income = self._val("His Total Income",QT_MOD='dollar')
        her_qt_income = self._val("Her Total Income",QT_MOD='dollar')
        total_income_qt = his_qt_income+her_qt_income
        tax_deferred_qt = self._val("His Tax Deferred",QT_MOD='dollar')+self._val("Her Tax Deferred",QT_MOD='dollar')
        job_income_ls, tax_deferred_ls = [total_income_qt], [tax_deferred_qt]
            # build out income lists with raises coming in steps on the first quarter of each year
        raise_yr = 1+self._val("Raise (%)",QT_MOD=False)
        for x in self._range_len(START=TODAY_QUARTER+1,LEN=working_qts-1,INCREMENT=1,ADD=True):
            if x%4 !=0:
                job_income_ls.append(job_income_ls[-1])
                tax_deferred_ls.append(tax_deferred_ls[-1])
            else:
                job_income_ls.append(job_income_ls[-1]*raise_yr)
                tax_deferred_ls.append(tax_deferred_ls[-1]*raise_yr)
        job_income_ls, tax_deferred_ls = job_income_ls +[0]*FI_qts,tax_deferred_ls +[0]*FI_qts # add the non-working years



    # values that are varied only due to controlable adjustable parameters
        # Her Pension
            # Calc max salary estimate
        fi_yr = math.trunc(self.fi_date)
        current_pension_salary_qt = her_qt_income/0.91 # Corrects for 9% taken from salary for pension
        remaining_working_years = fi_yr-TODAY_YR-1
        max_pension_salary_qt = current_pension_salary_qt * raise_yr ** remaining_working_years
            # find initial pension amount (in last working year's dollars)
        DE_ANZA_START_YEAR = 2016
        years_worked = fi_yr-DE_ANZA_START_YEAR
        pension_start_yr = self._val("Pension Year",False)
        pension_multiplier = float(self._val("Denica Pension",False)[str(pension_start_yr)])
        starting_pension_qt = max_pension_salary_qt * years_worked * pension_multiplier 
            # convert to est. value at pension_start_yr
        starting_pension_qt = starting_pension_qt*self._pow(FLAT_INFLATION,exp=(pension_start_yr-fi_yr))
            # build out list, add the correct number of zeros to the beginning
        pension_ls = [starting_pension_qt]
        for x in np.arange(pension_start_yr+0.25,time_ls[-1]+0.25,0.25):
            if x % 1 == 0:
                pension_ls.append(pension_ls[-1] * raise_yr)
            else:
                pension_ls.append(pension_ls[-1])
        pension_ls = [0]*(self.rows-len(pension_ls))+pension_ls
        
        # SS columns https://www.ssa.gov/oact/cola/Benefits.html 
        # Effect of Early or Delayed Retirement on Retirement Benefits: https://www.ssa.gov/oact/ProgData/ar_drc.html 
        # Index factors: https://www.ssa.gov/oact/cola/awifactors.html
        # Earnings limit: https://www.ssa.gov/benefits/retirement/planner/whileworking.html#:~:text=your%20excess%20earnings.-,How%20We%20Deduct%20Earnings%20From%20Benefits,full%20retirement%20age%20is%20%2451%2C960.
        # Bend points: https://www.ssa.gov/oact/cola/piaformula.html
        # PIA: https://www.ssa.gov/oact/cola/piaformula.html 
        #TODO: There's a lot of duplicated code here (his and her). Needs to be fed to another function, but many variables are local to main(), not global
            # pull data
        ss_data = pd.read_csv('ss_earnings.csv')
        ss_max_earnings, index_factors, ss_yrs = ss_data['SS_Max_Earnings'].tolist(), ss_data['Index_Factors'].tolist(), ss_data['Year'].tolist()
        his_ss_earnings, her_ss_earnings = ss_data['His_SS_Earnings'].tolist(), ss_data['Her_SS_Earnings'].tolist()
        ss_data_last_updated = ss_yrs[-1]
            # Extend all lists with predictions till fi year
        while ss_yrs[-1]<fi_yr-1:
            ss_yrs.append(ss_yrs[-1]+1)
            ss_max_earnings.append(ss_max_earnings[-1]*FLAT_INFLATION)
            his_ss_earnings.append(his_ss_earnings[-1]*raise_yr)
            her_ss_earnings.append(her_ss_earnings[-1]*raise_yr)
            index_factors.append(index_factors[-1]*(2-FLAT_INFLATION))        
            # index and limit the earnings, then sort them from high to low
        his_ss_earnings = [min(ss_max,earning)*index for ss_max, earning, index in zip(ss_max_earnings,his_ss_earnings, index_factors)]
        her_ss_earnings = [min(ss_max,earning)*index for ss_max, earning, index in zip(ss_max_earnings,her_ss_earnings, index_factors)]
        his_ss_earnings.sort(reverse=True)
        her_ss_earnings.sort(reverse=True)
            # Find Average Indexed Monthly Earnings (AIME), only top 35 years (420 months) count
        his_AIME, her_AIME = sum(his_ss_earnings[:35])/420, sum(her_ss_earnings[:35])/420
            # Calculate Primary Insurance Amounts (PIA) using bend points. Add AIME and sort to see where the AIME ranks in the bend points
        his_bend_points, her_bend_points = gov_params["Bend Points"]+[his_AIME], gov_params["Bend Points"]+[her_AIME]
        his_bend_points.sort()
        her_bend_points.sort()
                # cut off bend points at inserted AIME
        his_bend_points, her_bend_points = his_bend_points[:his_bend_points.index(his_AIME)+1], her_bend_points[:her_bend_points.index(her_AIME)+1]
        his_PIA_rates, her_PIA_rates = gov_params["His PIA Rates"], gov_params["Her PIA Rates"]
                # for the first bracket, just the bend times the rate. After that, find the marginal income to multiple by the rate
        his_full_PIA = sum([(his_bend_points[i]-his_bend_points[i-1])*rate if i!=0 else bend*rate for (i,bend), rate 
                   in zip(enumerate(his_bend_points),his_PIA_rates)])
        her_full_PIA = sum([(her_bend_points[i]-her_bend_points[i-1])*rate if i!=0 else bend*rate for (i,bend), rate 
                   in zip(enumerate(her_bend_points),her_PIA_rates)])
            # Find adjusted benefit amounts based on selected retirement age
        his_ss_age, her_ss_age = self._val("His SS Age",QT_MOD=False), self._val("Her SS Age",QT_MOD=False) 
        his_ss_year, her_ss_year = his_ss_age + 1993, her_ss_age + 1988 # uses 1 extra year since bday at end of year
            # convert to est. value at ss start-year and convert to quarterly (3 x monthly)
        his_PIA,her_PIA = his_full_PIA * gov_params['Benefit Rates'][str(his_ss_age)], her_full_PIA * gov_params['Benefit Rates'][str(her_ss_age)]
        his_ss_qt = 3 * his_PIA*self._pow(FLAT_INFLATION,exp=(his_ss_year-ss_data_last_updated)) # index factor is neutral to last update, so PIA is in that year's dollars
        her_ss_qt = 3 * her_PIA*self._pow(FLAT_INFLATION,exp=(her_ss_year-ss_data_last_updated))
            # build out list, add the correct number of zeros to the beginning, optimize later into list comprehension
        his_ss_ls = [his_ss_qt]
        for x in np.arange(his_ss_year+0.25,time_ls[-1]+0.25,0.25):
            if x % 1 == 0:
                his_ss_ls.append(his_ss_ls[-1] * raise_yr)
            else:
                his_ss_ls.append(his_ss_ls[-1])
        his_ss_ls = [0]*(self.rows-len(his_ss_ls))+his_ss_ls
        her_ss_ls = [her_ss_qt]
        for x in np.arange(her_ss_year+0.25,time_ls[-1]+0.25,0.25):
            if x % 1 == 0:
                her_ss_ls.append(her_ss_ls[-1] * raise_yr)
            else:
                her_ss_ls.append(her_ss_ls[-1])
        her_ss_ls = [0]*(self.rows-len(her_ss_ls))+her_ss_ls

        # Add all income together. 
            # is list comprehension faster than converting to numpy arr and adding, then converting back?
        total_income_ls = [sum([a,b,c,d]) for a, b, c, d in zip(job_income_ls,pension_ls, his_ss_ls, her_ss_ls)]

        # Taxes (brackets are for yearly, not qt, so need conversion)
        def get_taxes(income_qt):
            """Returns combined federal and state taxes on non-tax-deferred income"""
            fed_std_deduction = gov_params["Fed Std Deduction"]
            fed_tax_brackets = gov_params["Fed Bracket Rates"]
            state_std_deduction = gov_params["CA Std Deduction"]
            state_tax_brackets = gov_params["CA Bracket Rates"]
            fed_taxes = bracket_math(fed_tax_brackets,max(4*income_qt-fed_std_deduction,0))
            state_taxes = bracket_math(state_tax_brackets,max(4*income_qt-state_std_deduction,0))
            return 0.25 * (fed_taxes+state_taxes) # need to return quarterly taxes
        def bracket_math(bracket:list,income):
            rates,bend_points = zip(*bracket) # reverses the more readable format in the json file to the easier to use format for comprehension
            rates,bend_points = list(rates), list(bend_points) # they unzip as tuples for some reason
            bend_points += [income]
            bend_points.sort()
            bend_points = bend_points[:bend_points.index(income)+1]
            return sum([(bend_points[i]-bend_points[i-1])*rate if i!=0 else bend*rate for (i,bend), rate 
                   in zip(enumerate(bend_points),rates)])
            # taxes are 80% for pension and social security. Could optimze by skipping when sum of income is 0
        income_taxes = [sum([get_taxes(w2-deferred),0.8*get_taxes(pension+his_ss+her_ss)]) for w2,deferred, pension, his_ss, her_ss in zip(job_income_ls,tax_deferred_ls,pension_ls, his_ss_ls, her_ss_ls)]
            # FICA: Medicare (1.45% of income) and social security (6.2% of eligible income). Her income excluded from SS due to pension
        # fica = 0.0145*(SingleYear[HisIncomeCol]+SingleYear[HerIncomeCol])+0.062*Math.min(SSMaxEarnings,SingleYear[HisIncomeCol]) 
        medicare = [0.0145*job_income for job_income in job_income_ls]
            # need the SS Max Earnings, but in quarter form instead of the annual form I did in the SS section.
            # I've done this three times now, need to make it a function instead
        ss_max_earnings_qt =[0.25*ss_max_earnings[ss_yrs.index(TODAY_YR)]]
        for x in self._range_len(START=TODAY_QUARTER+1,LEN=working_qts-1,INCREMENT=1,ADD=True):
            if x%4 !=0:
                ss_max_earnings_qt.append(ss_max_earnings_qt[-1])
            else:
                ss_max_earnings_qt.append(ss_max_earnings_qt[-1]*FLAT_INFLATION)
        his_income_ratio = his_qt_income/(his_qt_income+her_qt_income)
        ss_tax = [0.062*min(his_income_ratio*income,ss_max) for income,ss_max in zip(job_income_ls,ss_max_earnings_qt)]
        ss_tax+= [0]*(self.rows-len(ss_tax))
        taxes_ls = [sum([a,b,c]) for a,b,c in zip(income_taxes,medicare,ss_tax)]

        
    # values that vary with the monte carlo randomness
        SavingsCol = 4
        InflationCol = 6
        SpendingCol = 15
        KidsCol = 16
        TotalCostsCol =17  
        SaveRateCol = 18
        ContributeCol = 19
        StockAlcCol = 20
        REAlcCol = 21
        BondAlcCol = 22
        StockReturnPctCol = 24
        REReturnPctCol = 25	
        BondReturnPctCol = 26
        ReturnPctCol = 27
        ReturnAmtCol = 28

# -------------------------------- FRAME -------------------------------- #






# -------------------------------- MONTE CARLO -------------------------------- #

# you should use zip() for making the total return column out of the 3 investment returns
# https://www.geeksforgeeks.org/python-iterate-multiple-lists-simultaneously/




# -------------------------------- HELPER FUNCTIONS -------------------------------- #

    def _catch(self, func, *args, handle=lambda e : e, **kwargs):
        # https://stackoverflow.com/questions/1528237/how-to-handle-exceptions-in-a-list-comprehensions
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # not sure how to implement this, so just hardcoding in return 0 for now, probably need to learn lambdas better
            # return handle(e) 
            return 0
    
    def _pow(self,num,exp:int):
        """exponential formular num^exp that should be faster for small exponents"""
        i=1
        result = num
        while i<exp:
            result = result * num
            i+=1
        return result
    
    def _val(self,KEY:str,QT_MOD):
        """MOD='rate' will return (1+r)^(1/4), MOD='dollar' will return d/4, MOD=False will return value"""
        if QT_MOD=="rate":
            return (1+self.params[KEY]) ** (1. / 4)
        elif QT_MOD=='dollar':
            return self.params[KEY] / 4
        elif not QT_MOD:
            return self.params[KEY]
        else:
            raise Exception("invalid MOD")
            
    
    def _range_len(self,START,LEN:int,INCREMENT,MULT=False,ADD=False):
        """Provide a range with a set START and set LENgth. If MULT set to True, Increment should be in (1+rate, ei: 1.03) format."""
        if ADD:
            return list(np.linspace(start=START,stop=START+INCREMENT*LEN,num=LEN,endpoint=False))
        elif MULT:
            # https://chrissardegna.com/blog/python-expontentiation-performance/
            return list(np.geomspace(start=START,stop=START*INCREMENT**LEN,num=LEN,endpoint=False))
        else:
            raise Exception("Didn't declare either MULT or ADD")
    
    def _clean_data(self, params: dict):
            for k, v in params.items():
                if type(v) is dict: # used for Denica pension parameter
                    continue
                elif v.isdigit():
                    params[k] = int(v)
                elif self._is_float(v):
                    params[k] = float(v)
                elif v == "True" or v == "False":
                    params[k] = bool(v)
            return params
        
    def _is_float(self, element: any):
        try:
            float(element)
            return True
        except ValueError:
            return False

# -------------------------------- JUST FOR TESTING -------------------------------- #

with open('params.json') as json_file:
            params = json.load(json_file)
param_vals = {key:obj["val"] for (key,obj) in params.items()}


if __name__ == '__main__':
    simulator = Simulator(param_vals)
    simulator.main()