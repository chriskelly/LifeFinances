import json, math, warnings, os, datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from models import returnGenerator
from data import constants as const

# For reference, something that has a 3% growth is a 0.03 return and 1.03 yield. That's how I'll define return and yield here
 
DEBUG_LVL = 1 # LVL 1: Print success rate, save worst failure, show plot | LVL 2: Investigate each result 1 by 1
SAVE_DIR = 'diagnostics/saved' 
TODAY = dt.date.today()
TODAY_QUARTER = (TODAY.month-1)//3
TODAY_YR = TODAY.year
TODAY_YR_QT = TODAY_YR+TODAY_QUARTER*.25
MONTE_CARLO_RUNS = 500 # takes 20 seconds to generate 5000
for file in os.scandir(SAVE_DIR): # delete previously saved files
    os.remove(file.path)

class Simulator:
    def __init__(self,param_vals):
        self.params = self._clean_data(param_vals)
        self.rows = int((param_vals['Calculate Til'] - TODAY_YR_QT)/.25)
        self.fi_date = self.params["FI Quarter"]
            
    def main(self):
# -------------------------------- VARIABLES -------------------------------- #      
    # ------------STATIC LISTS: TIME, JOB INCOME------------ #
        debug_lvl = DEBUG_LVL
        FLAT_INFLATION = self._val("Flat Inflation (%)",QT_MOD=False) # Used for some estimations like pension
        FLAT_INFLATION_QT = FLAT_INFLATION ** (1. / 4)
        
        # Year.Quarter list
        time_ls = self._range_len(START=TODAY_YR_QT,LEN=self.rows,INCREMENT=0.25,ADD=True)
        working_qts = int((self.fi_date-TODAY_YR_QT)/.25)
        FI_qts = self.rows-working_qts
        barista_qts = 4 * self._val("Barista Time (Yrs)",QT_MOD=False)
        
        # Job Income and tax-differed list. Does not include SS/Pensions. 
            # get quarterly income for his and her
        his_qt_income = self._val("His Total Income",QT_MOD='dollar')
        her_qt_income = self._val("Her Total Income",QT_MOD='dollar')
        total_income_qt = his_qt_income+her_qt_income
        tax_deferred_qt = self._val("His Tax Deferred",QT_MOD='dollar')+self._val("Her Tax Deferred",QT_MOD='dollar')
        total_barista_income_qt = self._val("Barista Income (Total)", QT_MOD='dollar') # Assuming no tax deferral for barista to be conservative and keep it easier
            # build out income lists with raises coming in steps on the first quarter of each year
        raise_yr = 1+self._val("Raise (%)",QT_MOD=False)
        job_income_ls = self._step_quarterize(total_income_qt,raise_yr,mode='working',working_qts=working_qts) if working_qts !=0 else []
        tax_deferred_ls = self._step_quarterize(tax_deferred_qt,raise_yr,mode='working',working_qts=working_qts) if working_qts !=0 else []
        barista_income_ls = self._range_len(START=total_barista_income_qt,LEN=barista_qts,INCREMENT=FLAT_INFLATION,MULT=True) # smooth growth is probably fine rather than step_quarterizing
            # add the non-working years
        job_income_ls  = job_income_ls + barista_income_ls + ([0] * (FI_qts - barista_qts)) 
        tax_deferred_ls = tax_deferred_ls + ([0]*FI_qts) 


    # ------------ PARAMETRIC DYNAMIC LISTS: PENSIONS, TAXES ------------ #
        # Her Pension
            # Calc max salary estimate
        fi_yr = math.trunc(self.fi_date)
        current_pension_salary_qt = her_qt_income/0.91 # Corrects for 9% taken from salary for pension
        if self._val('Pension Method',QT_MOD=False) == 'default':
            remaining_working_years = fi_yr-TODAY_YR-1
            max_pension_salary_qt = current_pension_salary_qt * raise_yr ** remaining_working_years
                # find initial pension amount (in last working year's dollars)
            DE_ANZA_START_YEAR = 2016
            years_worked = fi_yr-DE_ANZA_START_YEAR
            pension_start_yr = self._val("Pension Year",False)
            pension_multiplier = const.DENICA_PENSION_RATES[str(pension_start_yr)]
            starting_pension_qt = max_pension_salary_qt * years_worked * pension_multiplier 
                # convert to est. value at pension_start_yr
            starting_pension_qt = starting_pension_qt*self._pow(FLAT_INFLATION,exp=(pension_start_yr-fi_yr))
                # build out list, add the correct number of zeros to the beginning
            pension_ls =self._step_quarterize(starting_pension_qt,raise_yr,mode='pension',start_yr=pension_start_yr,time_ls=time_ls)
            pension_ls = [0]*(self.rows-len(pension_ls))+pension_ls
        elif self._val('Pension Method',QT_MOD=False) == 'cash-out':
            # Need to correct for out-dated info, first estimate salary at time of last update, then project forward
            data_age_qt = int((TODAY_YR_QT - const.PENSION_ACCOUNT_BAL_UP_DATE)/.25) # find age of data
            est_prev_pension_salary_qt = current_pension_salary_qt / (raise_yr ** (data_age_qt/4)) # estimate salary at time of data
            her_projected_income = self._step_quarterize(est_prev_pension_salary_qt,raise_yr,mode='working',working_qts=working_qts + data_age_qt) # project income from data age to FI
            pension_bal = const.PENSION_ACCOUNT_BAL
            pension_int_rate = const.PENSION_INTEREST_YIELD ** (1/4) - 1
            for income in her_projected_income:
                pension_bal += income * const.PENSION_COST + pension_bal * pension_int_rate
            pension_ls = [0] * working_qts + [pension_bal] + [0] * (FI_qts-1)
        
        # SS columns https://www.ssa.gov/oact/cola/Benefits.html 
        # Effect of Early or Delayed Retirement on Retirement Benefits: https://www.ssa.gov/oact/ProgData/ar_drc.html 
        # Index factors: https://www.ssa.gov/oact/cola/awifactors.html
        # Earnings limit: https://www.ssa.gov/benefits/retirement/planner/whileworking.html#:~:text=your%20excess%20earnings.-,How%20We%20Deduct%20Earnings%20From%20Benefits,full%20retirement%20age%20is%20%2451%2C960.
        # Bend points: https://www.ssa.gov/oact/cola/piaformula.html
        # PIA: https://www.ssa.gov/oact/cola/piaformula.html 
        ss_data = pd.read_csv('data/ss_earnings.csv')
        ss_max_earnings, index_factors, ss_yrs = ss_data['SS_Max_Earnings'].tolist(), ss_data['Index_Factors'].tolist(), ss_data['Year'].tolist()
        his_ss_earnings, her_ss_earnings = ss_data['His_SS_Earnings'].tolist(), ss_data['Her_SS_Earnings'].tolist()
        ss_data_last_updated = ss_yrs[-1]
            # Extend all lists with predictions till fi year
        while ss_yrs[-1] < self.fi_date - 1:
            ss_yrs.append(ss_yrs[-1]+1)
            ss_max_earnings.append(ss_max_earnings[-1]*FLAT_INFLATION)
            index_factors.append(index_factors[-1]*(2-FLAT_INFLATION))
            percent_of_year = 1.00 if ss_yrs[-1] != fi_yr else (self.fi_date - fi_yr) # add earnings for final partial years
            his_ss_earnings.append(his_ss_earnings[-1] * raise_yr * percent_of_year)
            her_ss_earnings.append(her_ss_earnings[-1] * raise_yr * percent_of_year)
            # Extend all lists with predictions till barista ends
        remaining_barista_qts = barista_qts 
        if percent_of_year < 1 and barista_qts > 0: # If there was a partial year and we're doing barista FI
            inflat_adj_barista_income_qt =  total_barista_income_qt * FLAT_INFLATION ** (ss_yrs[-1] - TODAY_YR)
            his_ss_earnings[-1] += (inflat_adj_barista_income_qt / 2) * min((4 * percent_of_year), barista_qts)
            her_ss_earnings[-1] += (total_barista_income_qt / 2) * min((4 * percent_of_year), barista_qts)
            remaining_barista_qts -= min((4 * percent_of_year), barista_qts)
        #while ss_yrs[-1] < self.fi_date + (barista_qts * 0.25) - 1:
        while remaining_barista_qts > 0:
            ss_yrs.append(ss_yrs[-1]+1)
            inflat_adj_barista_income_qt =  total_barista_income_qt * FLAT_INFLATION ** (ss_yrs[-1] - TODAY_YR)
            ss_max_earnings.append(ss_max_earnings[-1]*FLAT_INFLATION)
            index_factors.append(index_factors[-1]*(2-FLAT_INFLATION))
            his_ss_earnings.append(inflat_adj_barista_income_qt  * min(4 , remaining_barista_qts)) # quarterly barista income times remaining barista quarters
            her_ss_earnings.append(inflat_adj_barista_income_qt  * min(4 , remaining_barista_qts))  
            remaining_barista_qts -= 4
        def ss_calc(ss_earnings,PIA_rates,ss_age,birth_year):
            # index and limit the earnings, then sort them from high to low
            ss_earnings = [min(ss_max,earning)*index for ss_max, earning, index in zip(ss_max_earnings,ss_earnings, index_factors)]
            ss_earnings.sort(reverse=True)
            # Find Average Indexed Monthly Earnings (AIME), only top 35 years (420 months) count
            AIME = sum(ss_earnings[:35])/420
            # Calculate Primary Insurance Amounts (PIA) using bend points. Add AIME and sort to see where the AIME ranks in the bend points
            bend_points =const.SS_BEND_POINTS+[AIME]
            bend_points.sort()
             # cut off bend points at inserted AIME
            bend_points = bend_points[:bend_points.index(AIME)+1]
            # for the first bracket, just the bend times the rate. After that, find the marginal income to multiple by the rate
            full_PIA = sum([(bend_points[i]-bend_points[i-1])*rate if i!=0 else bend*rate for (i,bend), rate 
                                in zip(enumerate(bend_points),PIA_rates)])
            # Find adjusted benefit amounts based on selected retirement age
            ss_year = ss_age + birth_year
                # convert to est. value at ss start-year and convert to quarterly (3 x monthly)
            pia = full_PIA * const.BENEFIT_RATES[str(ss_age)]
            ss_qt = 3 * pia*self._pow(FLAT_INFLATION,exp=(ss_year-ss_data_last_updated)) # index factor is neutral to last update, so PIA is in that year's dollars
            # build out list, add the correct number of zeros to the beginning, optimize later into list comprehension
            ss_ls = self._step_quarterize(ss_qt,raise_yr,mode='pension',start_yr=ss_year,time_ls=time_ls)
            return [0]*(self.rows-len(ss_ls))+ss_ls
        his_ss_ls = ss_calc(his_ss_earnings,const.HIS_PIA_RATES,self._val("His SS Age",QT_MOD=False),birth_year=1993) # add 1 year to birth year since date is so late in year
        her_ss_ls = ss_calc(her_ss_earnings,const.HER_PIA_RATES,self._val("Her SS Age",QT_MOD=False),birth_year=1988) 

        # Add all income together. 
            # is list comprehension faster than converting to numpy arr and adding, then converting back?
        total_income_ls = [sum([a,b,c,d]) for a, b, c, d in zip(job_income_ls,pension_ls, his_ss_ls, her_ss_ls)]

        # Taxes (brackets are for yearly, not qt, so need conversion)
        def get_taxes(income_qt):
            """Returns combined federal and state taxes on non-tax-deferred income"""
            fed_taxes = bracket_math(const.FED_BRACKET_RATES,max(4*income_qt-const.FED_STD_DEDUCTION,0))
            state_taxes = bracket_math(const.CA_BRACKET_RATES,max(4*income_qt-const.CA_STD_DEDUCTION,0))
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
        ss_max_earnings_qt = self._step_quarterize(0.25*ss_max_earnings[ss_yrs.index(TODAY_YR)],FLAT_INFLATION,mode='working',working_qts=working_qts + barista_qts)
        his_income_ratio = his_qt_income/(his_qt_income+her_qt_income)
        ss_tax = [0.062*min(his_income_ratio*income,ss_max) for income,ss_max in zip(job_income_ls,ss_max_earnings_qt)]
        ss_tax+= [0]*(self.rows-len(ss_tax))
        taxes_ls = [sum([a,b,c]) for a,b,c in zip(income_taxes,medicare,ss_tax)]

        
    # ------------ MONTE CARLO VARIED LISTS: RETURN, INFLATION, SPENDING, ALLOCATION, NET WORTH ------------ #
        # variables that don't alter with each run
        stock_return_arr,bond_return_arr,re_return_arr,inflation_arr = returnGenerator.main(self.rows,4,MONTE_CARLO_RUNS) # bring in generated returns. Would prefer to use multiprocessing, but can't figure out how to get arrays of arrays handed back in .Value()
        spending_qt = self._val("Total Spending (Yearly)",QT_MOD='dollar')
        retirement_change = self._val("Retirement Change (%)",QT_MOD=False) # reduction of spending expected at retirement (less driving, less expensive cost of living, etc)
            # make a kids array with years of kids being planned. If GUI abilities are expanded, could save kid birth years in an unlimited array instead of limited to 3 kids
        kid_years = [kid for kid in [self._val("Year @ Kid #1",QT_MOD=False),self._val("Year @ Kid #2",QT_MOD=False),
                    self._val("Year @ Kid #3",QT_MOD=False)] if kid != '']
        kid_spending_rate = self._val("Cost of Kid (% Spending)",QT_MOD=False)
        # performance tracking
        success_rate = 0
        worst_failure_idx = self.rows
        failure_dict ={}
        # Monte Carlo
        for col in range(MONTE_CARLO_RUNS):
            stock_return_ls = stock_return_arr[col]
            bond_return_ls = bond_return_arr[col]
            re_return_ls = re_return_arr[col]
            inflation_ls = inflation_arr[col]
            # Spending, 
                # make list with spending increasing by corresponding inflation and changing at FI
            # spending_ls =[spending_qt*inflation if i<working_qts else spending_qt*inflation*(1+retirement_change) 
            #             for (i,inflation) in enumerate(inflation_ls)]
            # Kid count   
                # kids_ls should have kid for every year from each kid's birth till 22 years after
            kids_ls = [0]*self.rows
            for kid_yr in kid_years:
                kids_ls = [other_kids + 1 if yr_qt>=kid_yr and yr_qt-22<kid_yr else other_kids 
                        for other_kids,yr_qt in zip(kids_ls,time_ls) ]
            # Total costs
            #total_costs_ls = [sum([a,b,c]) for a,b,c in zip(taxes_ls,spending_ls,kids_ls)]
            # Net contributions to savings
            #contributions_ls = [income-costs for income, costs in zip(total_income_ls,total_costs_ls)]
            
            # Spending, kids, costs, contributions
            def base_spending(method:str,**kw):
                inflation = kw['inflation']
                if method == 'inflation-only':
                    spending = spending_qt*inflation if kw['working'] else spending_qt*inflation*(1+retirement_change)
                elif method == 'ceil-floor':
                    max_flux = self._val("Allowed Fluctuation (%)",QT_MOD=False)
                    # real spending should not increase/decrease more than the max_flux (should it be symetric?)
                    # only takes effect after retirement
                    # reactant to market, not sure how. Maybe try to maintain last withdrawal percentage til you reach max_flux?
                        # could use a pre-set withdrawal rate?
                        # could just swing back and forth depending if markets are above/below average
                    equity_mean_qt = const.EQUITY_MEAN ** (1/4) - 1
                    bond_mean_qt =  const.BOND_MEAN ** (1/4) - 1
                    re_mean_qt = const.RE_MEAN ** (1/4) - 1
                    expected_return_rate_qt = equity_mean_qt *kw['alloc']['Equity'] + bond_mean_qt *kw['alloc']['Bond'] + re_mean_qt *kw['alloc']['RE']
                    spending = spending_qt*inflation if kw['working'] else spending_qt*inflation*(1+retirement_change)
                    if kw['return_rate'] is not None:
                        spending = spending*(1+max_flux) if kw['return_rate'] > expected_return_rate_qt else spending*(1-max_flux)
                return spending
            # Allocation between equity, RE and bonds. Allows for different methods to be designed
            def allocation(method:str,**kw):
                """Return a dict {"Equity":EquityAlloc, "RE":REAlloc, "Bond":BondAlloc} \n
                method = 'Life Cycle' -> needs kw['inflation'] and kw['net_worth']"""
                if method == 'Life Cycle':
                    re_ratio = self.params["RE Ratio"]
                    equity_target = self.params["Equity Target"] 
                    max_risk_factor = 1 # You could put this in params if you wanted to be able to modify max risk (in the case of using margin) 
                    equity_target_PV = equity_target*kw['inflation'] # going to differ to from the Google Sheet since equity target was pegged to FI years rather than today's dollars
                    risk_factor = min(max(equity_target_PV/max(kw['net_worth'],0.000001),0),max_risk_factor) # need to avoid ZeroDivisionError
                    with warnings.catch_warnings(): # https://stackoverflow.com/a/14463362/13627745 # another way to avoid ZeroDivisionError, but also avoid printing out exceptions
                        warnings.simplefilter("ignore")
                        try: re_alloc = (risk_factor*re_ratio)/((1-re_ratio)*(1+risk_factor*re_ratio/(1-re_ratio))) # derived with fun algebra! ReAlloc = RERatio*(ReAlloc+EquityTotal); EquityTotal = RiskFactor*OriginalEquity; ReAlloc+OriginalEquity=100%
                        except ZeroDivisionError: re_alloc = (risk_factor*re_ratio)
                    equity_alloc = (1-re_alloc)*risk_factor
                    bond_alloc = max(1-re_alloc-equity_alloc,0) 
                    return {"Equity":equity_alloc,"RE":re_alloc,"Bond":bond_alloc}
            # Net Worth/total savings
            spending_ls, total_costs_ls, contributions_ls, equity_alloc_ls, re_alloc_ls, bond_alloc_ls = [],[],[],[],[],[]
            return_rate = None
                # loop through time_ls to find net worth changes
            for i in range(self.rows): 
                if i == 0: net_worth_ls = [self._val('Current Net Worth ($)',QT_MOD=False)]
                alloc = allocation(method='Life Cycle',inflation=inflation_ls[i],net_worth = net_worth_ls[-1])
                equity_alloc_ls.append(alloc["Equity"])
                re_alloc_ls.append(alloc["RE"])
                bond_alloc_ls.append(alloc["Bond"])
                working = True if i<working_qts else False
                spend_method = self._val("Spending Method",QT_MOD=False)
                spending_ls.append(base_spending(method=spend_method, inflation=inflation_ls[i], 
                                                 working=working, alloc=alloc,return_rate=return_rate))
                kids_ls[i] = spending_ls[i] * kid_spending_rate * kids_ls[i]
                total_costs_ls.append(taxes_ls[i] + spending_ls[i] + kids_ls[i])
                contributions_ls.append(total_income_ls[i] - total_costs_ls[i])
                return_rate = stock_return_ls[i]*alloc['Equity'] + bond_return_ls[i]*alloc['Bond'] + re_return_ls[i]*alloc['RE']
                return_amt = return_rate*(net_worth_ls[-1]+0.5*contributions_ls[i])
                net_worth_ls.append(max(0,net_worth_ls[-1]+return_amt+contributions_ls[i]))
            net_worth_ls.pop()
            if net_worth_ls[-1]!=0: 
                success_rate += 1
            if 0 in net_worth_ls and net_worth_ls.index(0) < worst_failure_idx and debug_lvl >= 1:
                worst_failure_idx = net_worth_ls.index(0)
                failure_dict = {
                    "Time":time_ls,
                    "Net Worth":net_worth_ls,
                    "Job Income":job_income_ls,
                    "Tax Deferred":tax_deferred_ls,
                    "Pension":pension_ls,
                    "His SS":his_ss_ls,
                    "Her SS":her_ss_ls,
                    "Total Income":total_income_ls,
                    "Income Taxes":income_taxes,
                    "Medicare Taxes":medicare,
                    "SS Taxes":ss_tax,
                    "Total Taxes":taxes_ls,
                    "Inflation":inflation_ls,
                    "Spending":spending_ls,
                    "Kid Costs":kids_ls,
                    "Total Costs":total_costs_ls,
                    "Contributions":contributions_ls,
                    "Stock Alloc":equity_alloc_ls,
                    "Bond Alloc":bond_alloc_ls,
                    "RE Alloc":re_alloc_ls,
                    "Stock Returns":stock_return_ls,
                    "Bond Returns":bond_return_ls,
                    "RE Returns":re_return_ls
                }
            if debug_lvl >= 1: plt.plot(time_ls,net_worth_ls)
            if debug_lvl >= 2: 
                plt.show()
                usr_input = input("save (s), next (n), continue (c)?")
                if usr_input == 's':
                    save_dict = {
                        "Time":time_ls,
                        "Net Worth":net_worth_ls,
                        "Job Income":job_income_ls,
                        "Tax Deferred":tax_deferred_ls,
                        "Pension":pension_ls,
                        "His SS":his_ss_ls,
                        "Her SS":her_ss_ls,
                        "Total Income":total_income_ls,
                        "Income Taxes":income_taxes,
                        "Medicare Taxes":medicare,
                        "SS Taxes":ss_tax,
                        "Total Taxes":taxes_ls,
                        "Inflation":inflation_ls,
                        "Spending":spending_ls,
                        "Kid Costs":kids_ls,
                        "Total Costs":total_costs_ls,
                        "Contributions":contributions_ls,
                        "Stock Alloc":equity_alloc_ls,
                        "Bond Alloc":bond_alloc_ls,
                        "RE Alloc":re_alloc_ls,
                        "Stock Returns":stock_return_ls,
                        "Bond Returns":bond_return_ls,
                        "RE Returns":re_return_ls
                    }
                    save_df = pd.DataFrame.from_dict(save_dict)
                    save_df.to_csv(f'{SAVE_DIR}/saveData{col}.csv')
                elif usr_input == 'c':
                    debug_lvl = 1
        success_rate = success_rate/MONTE_CARLO_RUNS
        if debug_lvl >= 1: 
            failure_df = pd.DataFrame.from_dict(failure_dict)
            failure_df.to_csv(f'{SAVE_DIR}/worst_failure.csv')
            print(f"Success Rate: {success_rate*100:.2f}%")
        
        if debug_lvl >= 1: plt.show()
        return success_rate
        
        debug_point = None
        

# -------------------------------- HELPER FUNCTIONS -------------------------------- #

    def _step_quarterize(self,first_val,increase_yield,mode,**kw):
        """Return a list with values that step up on a yearly basis rather than quarterly \n
        mode = 'working' -> from today_qt to fi_date, needs kw['working_qts'] \n
        mode = 'pension' -> from provided kw['start_yr'] to end of kw['time_ls']"""
        ls = [first_val]
        if mode == 'working':
            if kw["working_qts"] == 0: return [] # if fi_date = TODAY_YR_QT, the returned range should be empty
            custom_range = self._range_len(START=TODAY_QUARTER+1,LEN=kw["working_qts"]-1,INCREMENT=1,ADD=True) # subtracing one len since you already have the first value
            [ls.append(ls[-1]) if x%4 !=0 else ls.append(ls[-1]*increase_yield) for x in custom_range]
        elif mode == 'pension':
            custom_range = np.arange(kw['start_yr']+0.25,kw['time_ls'][-1]+0.25,0.25)
            [ls.append(ls[-1]*increase_yield) if x%1 ==0 else ls.append(ls[-1]) for x in custom_range]
        return ls
                
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
        """MOD='rate' will return (1+r)^(1/4) \n 
        MOD='dollar' will return d/4 \n 
        MOD=False will return value"""
        if QT_MOD=="rate":
            return (1+self.params[KEY]) ** (1. / 4)
        elif QT_MOD=='dollar':
            return self.params[KEY] / 4
        elif not QT_MOD:
            return self.params[KEY]
        else:
            raise Exception("invalid MOD")
            
    
    def _range_len(self,START,LEN:int,INCREMENT,MULT=False,ADD=False):
        """Provide a range with a set START and set LENgth. If MULT set to True, Increment should be in yield (1+rate, ei: 1.03) format."""
        if ADD:
            return list(np.linspace(start=START,stop=START+INCREMENT*LEN,num=LEN,endpoint=False))
        elif MULT:
            # https://chrissardegna.com/blog/python-expontentiation-performance/
            return list(np.geomspace(start=START,stop=START*INCREMENT**LEN,num=LEN,endpoint=False))
        else:
            raise Exception("Didn't declare either MULT or ADD")
    
    def _clean_data(self, params: dict):
            for k, v in params.items():
                if type(v) is dict:
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

with open(const.PARAMS_LOC) as json_file:
            params = json.load(json_file)
param_vals = {key:obj["val"] for (key,obj) in params.items()}


if __name__ == '__main__':
    simulator = Simulator(param_vals)
    simulator.main()