"""Retirement Planning Simulator

This script allows the user to model the success rate of a retirement plan
with parameters defined in data/data.db.

Required installations are detailed in requirements.txt.

This file can also be imported as a module and contains the following functions:

    * Simulator.main() - runs a simulation and returns the success rate, the
                            returns used, and image data of the results
    * Simulator.val() - returns the value of a specific parameter
    * step_quarterize() - Creates a list with values that increases only at the new year
    * get_taxes() - Combines federal and state taxes on non-tax-deferred income
    * bracket_math() - Calculates and return taxes owed for specific brackets
    * test_unit() - Creates a Simulator with only 1 monte carlo run
"""

import statistics
import warnings
import os
import sys
import io
import base64
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from data import constants as const
from models import return_generator, annuity, model, social_security, income
import git

git_root= git.Repo(os.path.abspath(__file__),
                   search_parent_directories=True).git.rev_parse('--show-toplevel')
sys.path.append(git_root)

if os.path.exists(const.SAVE_DIR):
    for file in os.scandir(const.SAVE_DIR): # delete previously saved files
        os.remove(file.path)
else:
    os.makedirs(const.SAVE_DIR)

MONTE_CARLO_RUNS = 500 # takes 20 seconds to generate 5000
DEBUG_LVL = 2 
# DEBUG_LVL 1: Generate plot
# DEBUG_LVL 2: Print success rate, save worst failure, show plot
# DEBUG_LVL 3: Investigate each result 1 by 1

class Simulator:
    """
    This class can simulate the income and expenses of a user and their partner
    given the desired parameters. The adjustable parameters are all located in
    data/params.json
    
    The default unit of time is a quarter of a year. Calculations are not done
    per year.
    The default unit for money is $1,000 USD (e.g. thousands)
    
    Return/rate/yield definitions: something that has a 3% growth is a 0.03  
    return/rate and 1.03 yield
    
    Attributes
    ----------
    params : dict
        A clean set of parameters and their values
    rows : int
        The total number of periods per simulation
    admin : bool
    fi_date : ?
    override_dict : dict
        A dictionary for parameters that you want to override
    
    Methods
    -------
    main()
        Creates data and runs the Montecarlo simulations
    get_pension_payment()
        Calculates pension per quarter
    base_spending()
        Calculates quarterly expenses
    allocation()
        Determines the allocation of investments per quarter
    
    """
    def __init__(self, param_vals, override_dict={}):
        """
        Construct a Simulator out of the params in the given model

        Parameters
        ----------
        param_vals : Dict
            A dictionary with {param : val}
        override_dict : dict, optional
            Use this input to override named parameters. The default is {}.
                'monte_carlo_runs':int : Overrides the constant MONTE_CARLO_RUNS
                'returns':[stock_return_arr,bond_return_arr,re_return_arr,inflation_arr] : Overrides return data

        Returns
        -------
        None.

        """
        self.params = param_vals
        self.rows = int((param_vals['calculate_til'] - model.TODAY_YR_QT)/.25)
        self.admin = self.params["admin"] # Are you Chris?
        self.partner = self.params["partner"]
        self.override_dict = override_dict
            
    def main(self) -> dict:
        """Runs a simulation with the parameters in data/data.db

        Returns:
            dict: {
                's_rate':success_rate, 
                'returns':[stock_return_arr,bond_return_arr,re_return_arr,inflation_arr], 
                'img_data':base64 encoded image of simulation results
                }
        """
# -------------------------------- VARIABLES -------------------------------- #      
    # STATIC LISTS: TIME, JOB INCOME --------------------------------------- #

        debug_lvl = DEBUG_LVL
        if debug_lvl >= 1: fig = plt.figure()
        
        # Year.Quarter list 
        date_ls = self._range_len(START=model.TODAY_YR_QT,LEN=self.rows,INCREMENT=0.25,ADD=True) 
        
        # Job Income and tax-differed list. Does not include SS. 
        user_income_calc = income.Calculator(self.val("user_jobs",QT_MOD=False),date_ls)
        partner_income_calc = income.Calculator(self.val("partner_jobs",QT_MOD=False),date_ls) if self.partner else None
        (job_income_ls, tax_deferred_ls) = income.generate_lists(user_income_calc,partner_income_calc)
        # FICA: Medicare (1.45% of income) and social security (6.2% of eligible income)
        medicare= np.array(job_income_ls)*0.0145
        ss_tax = social_security.taxes(date_ls,const.PENSION_INFLATION,user_income_calc,partner_income_calc)
        
    # MONTE CARLO VARIED LISTS: RETURN, INFLATION, SPENDING, ALLOCATION, NET WORTH ------------ #
        # variables that don't alter with each run
        if 'monte_carlo_runs' in self.override_dict:
            monte_carlo_runs = self.override_dict['monte_carlo_runs']
        else:
            monte_carlo_runs = MONTE_CARLO_RUNS
        if 'returns' in self.override_dict:
            stock_return_arr,bond_return_arr,re_return_arr,inflation_arr = self.override_dict['returns']
        else:
            # bring in generated returns. Would prefer to use multiprocessing, but can't figure out how to get arrays of arrays handed back in .Value()
            stock_return_arr,bond_return_arr,re_return_arr,inflation_arr = return_generator.main(self.rows,4,monte_carlo_runs) 
        spending_qt = self.val("yearly_spending",QT_MOD='dollar')
        retirement_change = self.val("retirement_spending_change",QT_MOD=False) # reduction of spending expected at retirement (less driving, less expensive cost of living, etc)
            # make a kids array with years of kids being planned
        kid_year_qts = [year_qt for _,year_qt in self.val("kid_birth_years",QT_MOD=False)]
        kid_spending_rate = self.val("cost_of_kid",QT_MOD=False)
            # Social Security Initialization
        user_ss_calc = social_security.Calculator(self,'user',date_ls,user_income_calc)
        partner_ss_calc = social_security.Calculator(self,'partner',date_ls,partner_income_calc,spouse_calc=user_ss_calc) if self.partner else None
            # performance tracking
        success_rate = 0
        final_net_worths = [] # Establish empty list to calculate net worth median
        worst_failure_idx = self.rows
        failure_dict ={}
        
        # Monte Carlo
        for col in range(monte_carlo_runs):
            # check for cancellation
            if os.path.exists(const.QUIT_LOC):
                os.remove(const.QUIT_LOC)
                return {}
            stock_return_ls = stock_return_arr[col]
            bond_return_ls = bond_return_arr[col]
            re_return_ls = re_return_arr[col]
            inflation_ls = inflation_arr[col]
            # Social Security List Creation
            user_ss_calc.make_list(inflation_ls)
            if self.partner: partner_ss_calc.make_list(inflation_ls)
            # Kid count   
                # kids_ls should have kid for every year from each kid's birth till 22 years after
            kids_ls = [0]*self.rows
            for kid_yr in kid_year_qts:
                kids_ls = [other_kids + 1 if yr_qt>=kid_yr and yr_qt-22<kid_yr else other_kids 
                        for other_kids,yr_qt in zip(kids_ls,date_ls) ]
            # Net Worth/total savings
            spending_ls, total_costs_ls, net_transaction_ls, equity_alloc_ls = [],[],[],[]
            re_alloc_ls, bond_alloc_ls, taxes_ls, total_income_ls, usr_ss_ls, partner_ss_ls = [],[],[],[],[],[]
            return_rate = None
            my_annuity = annuity.Annuity()
            annuity_ls = np.zeros(self.rows)
                # loop through date_ls to find net worth changes
            net_worth_ls = [self.val('current_net_worth',QT_MOD=False)]
            
            for row in range(self.rows): 
                # allocations
                alloc = self._allocation(inflation_ls[row],net_worth_ls[-1],date_ls,row)
                equity_alloc_ls.append(alloc["Equity"])
                re_alloc_ls.append(alloc["RE"])
                bond_alloc_ls.append(alloc["Bond"])
                # social security 
                trust = self.val("pension_trust_factor",QT_MOD=False)
                usr_ss_ls.append(trust * user_ss_calc.get_payment(row,net_worth_ls[-1],self.val("equity_target",QT_MOD=False)))
                if self.partner:
                    partner_ss_ls.append(trust * partner_ss_calc.get_payment(row,net_worth_ls[-1],self.val("equity_target",QT_MOD=False)))
                else: partner_ss_ls.append(0)
                # taxes
                    # taxes are 80% for pension and social security
                income_tax = get_taxes(job_income_ls[row]-tax_deferred_ls[row],inflation_ls[row],self.partner) \
                            + 0.8*get_taxes(usr_ss_ls[row]+ partner_ss_ls[row],inflation_ls[row],self.partner)
                taxes_ls.append(income_tax + medicare[row] + ss_tax[row])
                # spending
                if job_income_ls[row] == 0:
                    working = False
                else: working = True
                spending_ls.append(self._base_spending(spending_qt, retirement_change,
                                                      inflation=inflation_ls[row], 
                                                 working=working, alloc=alloc,return_rate=return_rate))
                kids_ls[row] = spending_ls[row] * kid_spending_rate * kids_ls[row]
                total_costs_ls.append(taxes_ls[row] + spending_ls[row] + kids_ls[row])
                total_income_ls.append(job_income_ls[row]+usr_ss_ls[row]+ partner_ss_ls[row])
                net_transaction_ls.append(total_income_ls[row] - total_costs_ls[row])
                # annuity contributions
                if alloc['Annuity'] != 0: 
                    target_balance = alloc['Annuity'] * net_worth_ls[-1]
                    contribution = max(0, target_balance - my_annuity.balance_update(row))
                    my_annuity.contribute(contribution,row)
                    annuity_ls[row] -= contribution
                    net_worth_ls[-1] -= contribution
                # investment returns
                return_rate = stock_return_ls[row]*alloc['Equity'] + bond_return_ls[row]*alloc['Bond'] + re_return_ls[row]*alloc['RE']
                return_amt = return_rate*(net_worth_ls[-1]+0.5*net_transaction_ls[row])
                # annuity withdrawals
                if net_worth_ls[-1]+return_amt+net_transaction_ls[row] < 0 and not my_annuity.annuitized: # annuity is started when user runs out of money
                    my_annuity.annuitize(row)
                annuity_ls[row] += my_annuity.take_payment() 
                net_transaction_ls[row] += my_annuity.take_payment()                
                # if net withdrawal, apply portfolio tax before pulling from net worth
                if net_transaction_ls[row] < 0:
                    portfolio_tax = -net_transaction_ls[row] * (1/(1-self.val("drawdown_tax_rate",QT_MOD=False)) - 1)
                    taxes_ls[row] += portfolio_tax
                    net_transaction_ls[row] -= portfolio_tax
                if net_worth_ls[-1] >= 0: # prevent net worth from exponentially decreasing below 0
                    net_worth_ls.append(max(0,net_worth_ls[-1]+return_amt+net_transaction_ls[row]))
                else: # if net worth started negative, assume no investing until positive net worth
                    net_worth_ls.append(net_worth_ls[-1]+net_transaction_ls[row])
            net_worth_ls.pop()
            if net_worth_ls[-1]!=0: 
                success_rate += 1
            final_net_worths.append(net_worth_ls[-1]) # Add final net worth to list for later calculation
            if 0 in net_worth_ls and net_worth_ls.index(0) < worst_failure_idx and debug_lvl >= 2:
                worst_failure_idx = net_worth_ls.index(0)
                failure_dict = {
                    "Date":date_ls,
                    "Net Worth":net_worth_ls,
                    "Job Income":job_income_ls,
                    "Tax Deferred":tax_deferred_ls,
                    "User SS":usr_ss_ls,
                    "Partner SS":partner_ss_ls,
                    "Total Income":total_income_ls,
                    "Total Taxes":taxes_ls,
                    "Inflation":inflation_ls,
                    "Spending":spending_ls,
                    "Kid Costs":kids_ls,
                    "Total Costs":total_costs_ls,
                    "Net Transaction":net_transaction_ls,
                    "Annuity":annuity_ls,
                    "Stock Alloc":equity_alloc_ls,
                    "Bond Alloc":bond_alloc_ls,
                    "RE Alloc":re_alloc_ls,
                    "Stock Returns":stock_return_ls,
                    "Bond Returns":bond_return_ls,
                    "RE Returns":re_return_ls
                }
            if debug_lvl >= 1: 
                plt.plot(date_ls,net_worth_ls)
                plt.ylabel('net worth, $1,000s')
                plt.xlabel('time')
            if debug_lvl >= 3: 
                plt.show()
                usr_input = input("save (s), next (n), continue (c)?")
                if usr_input == 's':
                    save_dict = {
                        "Date":date_ls,
                        "Net Worth":net_worth_ls,
                        "Job Income":job_income_ls,
                        "Tax Deferred":tax_deferred_ls,
                        "User SS":usr_ss_ls,
                        "Partner SS":partner_ss_ls,
                        "Total Income":total_income_ls,
                        "Total Taxes":taxes_ls,
                        "Inflation":inflation_ls,
                        "Spending":spending_ls,
                        "Kid Costs":kids_ls,
                        "Total Costs":total_costs_ls,
                        "Net Transaction":net_transaction_ls,
                        "Annuity":annuity_ls,
                        "Stock Alloc":equity_alloc_ls,
                        "Bond Alloc":bond_alloc_ls,
                        "RE Alloc":re_alloc_ls,
                        "Stock Returns":stock_return_ls,
                        "Bond Returns":bond_return_ls,
                        "RE Returns":re_return_ls
                    }
                    save_df = pd.DataFrame.from_dict(save_dict)
                    save_df.to_csv(f'{const.SAVE_DIR}/saveData{col}.csv')
                elif usr_input == 'c':
                    debug_lvl = 2
        #Summarize the results of the simulations
        success_rate = success_rate/monte_carlo_runs
        median_net_worth = statistics.median(final_net_worths)
        img_data = None
        if debug_lvl >= 1: # embed image for flask https://matplotlib.org/stable/gallery/user_interfaces/web_application_server_sgskip.html
            buf = io.BytesIO() # Save it to a temporary buffer.
            fig.savefig(buf, format="png")
            img_data = base64.b64encode(buf.getbuffer()).decode("ascii") # Embed the result in the html output.
        if debug_lvl >= 2:
            plt.show()
            failure_df = pd.DataFrame.from_dict(failure_dict)
            failure_df.to_csv(f'{const.SAVE_DIR}/worst_failure.csv')
            print(f"Success Rate: {success_rate*100:.2f}%")
            print(f"Median Final Net Worth: ${median_net_worth*1000:,.0f}")
        
        return {'s_rate':success_rate, 'returns':[stock_return_arr,bond_return_arr,re_return_arr,inflation_arr], 'img_data':img_data}
        
        debug_point = None
        

    # HELPER FUNCTIONS ---------------------------------------------------- #     
    def _pow(self,num,exp:int) -> int:
        """exponential formular num^exp that should be faster for small exponents"""
        i=1
        result = num
        while i<exp:
            result = result * num
            i+=1
        return result
    
    def val(self,KEY:str,QT_MOD):
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
            
    def _range_len(self,START,LEN:int,INCREMENT,MULT=False,ADD=False) -> list:
        """Provide a range with a set START and set LENgth. If MULT set to True, Increment should be in yield (1+rate, ei: 1.03) format."""
        if ADD:
            return list(np.linspace(start=START,stop=START+INCREMENT*LEN,num=LEN,endpoint=False))
        elif MULT:
            # https://chrissardegna.com/blog/python-expontentiation-performance/
            return list(np.geomspace(start=START,stop=START*INCREMENT**LEN,num=LEN,endpoint=False))
        else:
            raise Exception("Didn't declare either MULT or ADD")
        
    def _base_spending(self,spending_qt, retirement_change,**kw):
        """Calculates base spending in a quarter

        Parameters
        ----------
        spending_qt : numeric
            DESCRIPTION.
        retirement_change : numeric
            DESCRIPTION.

        Returns
        -------
        spending : numeric
            Dollar value of spending for one quarter.

        """
        # Spending, kids, costs, contributions
        method= self.val("spending_method",QT_MOD=False)
        inflation = kw['inflation']
        if method == 'inflation-only':
            spending = spending_qt*inflation if kw['working'] else spending_qt*inflation*(1+retirement_change)
        elif method == 'ceil-floor':
            max_flux = self.val("allowed_fluctuation",QT_MOD=False)
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
    
    def _allocation(self, inflation:float, net_worth:float, date_ls:list, row:int):
        """Calculates allocation between equity, RE, bonds, and annuities. 
        Allows for different methods to be used

        Args:
            inflation (float): Inflation value at this row
            net_worth (float): Net worth at this row
            date_ls (list): List of dates
            row (int)

        Raises:
            ValueError: If a valid method is not provided

        Returns:
            dict: {'Equity':Equity Allocation,'RE':Real Estate Allocations,'Bond':Bond Allocation,'Annuity':Annuity Allocation}
        """
        # variables used in multiple method
        method= self.val("allocation_method",QT_MOD=False)
        re_ratio = self.val("real_estate_equity_ratio",QT_MOD=False)
        if method == 'Life Cycle':
            equity_target = self.val("equity_target",QT_MOD=False) 
            equity_target_PV = equity_target*inflation # going to differ to from the Google Sheet since equity target was pegged to FI years rather than today's dollars
            max_risk_factor = 1 # You could put this in params if you wanted to be able to modify max risk (in the case of using margin) 
            risk_factor = min(max(equity_target_PV/max(net_worth,0.000001),0),max_risk_factor) # need to avoid ZeroDivisionError
            with warnings.catch_warnings(): # https://stackoverflow.com/a/14463362/13627745 # another way to avoid ZeroDivisionError, but also avoid printing out exceptions
                warnings.simplefilter("ignore")
                try: 
                    re_alloc = (risk_factor*re_ratio)/((1-re_ratio)*(1+risk_factor*re_ratio/(1-re_ratio))) # derived with fun algebra! ReAlloc = RERatio*(ReAlloc+EquityTotal); EquityTotal = RiskFactor*OriginalEquity; ReAlloc+OriginalEquity=100%
                except ZeroDivisionError: 
                    re_alloc = (risk_factor*re_ratio)
            equity_alloc = (1-re_alloc)*risk_factor
            bond_alloc = max(1-re_alloc-equity_alloc,0) 
        elif method == 'Flat':
            bond_alloc = self.val("flat_bond_target",QT_MOD=False) 
            re_alloc = re_ratio * (1-bond_alloc)
            equity_alloc = 1 - bond_alloc - re_alloc
        elif method == '120 Minus Age' or method == '110 Minus Age' or method == '100 Minus Age':
            risk_val = int(method[0:3])
            average_age = (self.val("user_age",False) + self.val("partner_age",False))/2 + row/4
            bond_alloc = max(0, 1 - (risk_val - average_age)/100)
            re_alloc = re_ratio * (1-bond_alloc)
            equity_alloc = 1 - bond_alloc - re_alloc
        elif method == 'Bond Tent':
            start_bond_alloc = self.val("bond_tent_start_allocation",QT_MOD=False) 
            start_date = self.val("bond_tent_start_date",QT_MOD=False) 
            peak_bond_alloc = self.val("bond_tent_peak_allocation",QT_MOD=False) 
            peak_date = self.val("bond_tent_peak_date",QT_MOD=False) 
            end_bond_alloc = self.val("bond_tent_end_allocation",QT_MOD=False) 
            end_date = self.val("bond_tent_end_date",QT_MOD=False) 
            start_date = max(model.TODAY_YR_QT,start_date) # prevent start date from going too low due to genetic improvement trials
            start_row, peak_row, end_row = date_ls.index(start_date), date_ls.index(peak_date), date_ls.index(end_date)
            if row <= start_row: # Initial flat period
                bond_alloc = start_bond_alloc
            elif row < peak_row: # Climb to peak
                bond_alloc = np.interp(row, [start_row,peak_row], [start_bond_alloc,peak_bond_alloc])
            elif row == peak_row: # Peak point
                bond_alloc = peak_bond_alloc
            elif row < end_row: # Descend to new flat
                bond_alloc = np.interp(row, [peak_row,end_row], [peak_bond_alloc,end_bond_alloc])
            elif row >= end_row: # Flat period
                bond_alloc = end_bond_alloc
            re_alloc = re_ratio * (1-bond_alloc)
            equity_alloc = 1 - bond_alloc - re_alloc
        else: 
            raise ValueError("Allocation method is not defined")
        # Convert bonds to annuities depending on params
        if self.val("annuities_instead_of_bonds",QT_MOD=False):
            annuity_alloc = bond_alloc
            bond_alloc = 0
        else:
            annuity_alloc = 0
        output= {"Equity":equity_alloc,
                "RE":re_alloc,
                "Bond":bond_alloc,
                "Annuity":annuity_alloc}
        return output
    
# ADDITIONAL HELPER FUNCTIONS ------------------------------------------- #
#These functions do not requre the class
def step_quarterize(date_ls:list,first_val,increase_yield,start_date_idx:int,end_date_idx:int) -> list:
    """Creates list with a value that increases only at the new year

    Args:
        date_ls (list)
        first_val (_type_): intial value
        increase_yield (_type_): growth expected each year in 1.04 format
        start_date_idx (int): index of the date_ls that it starts at
        end_date_idx (int): index of the date_ls that it ends at (inclusive)

    Returns:
        list
    """
    ls = [first_val]
    for date in date_ls[start_date_idx+1:end_date_idx+1]: # +1 on end_date_idx due to non-inclusivity of list splicing
        if date%1 == 0:
            ls.append(ls[-1] * increase_yield)
        else:
            ls.append(ls[-1])
    return ls

def get_taxes(income_qt:float,inflation:float,married_state:bool) -> float:
    """Combines federal and state taxes on non-tax-deferred income

    Args:
        income_qt (float): income in quarterly amount
        inflation (float): inflation at specific date
        married_state (bool): True if married, False if single

    Returns:
        (float): federal and state tax burden for that quarter
    """
    if(income_qt == 0.0): return 0 # avoid bracket math if no income
    
    adj_income = 4*income_qt / inflation # convert income to yearly and adjust backward for inflation    
    fed_taxes = bracket_math(const.FED_BRACKET_RATES[married_state],max(adj_income-const.FED_STD_DEDUCTION[married_state],0))
    state_taxes = bracket_math(const.STATE_BRACKET_RATES[married_state],max(adj_income-const.STATE_STD_DEDUCTION[married_state],0))
    return 0.25 * (fed_taxes+state_taxes) # need to return quarterly taxes

def bracket_math(brackets:list,yr_income:float) -> float:
    """Calculates and returns taxes owed

    Args:
        brackets (list): List of brackets in format: [rate,highest dollar that rate applies to,sum of tax owed in previous brackets]
        yr_income (float): income in yearly amount

    Returns:
        (float): tax owed
    """
    if(yr_income == 0.0): return 0 # avoid bracket math if no income
    rate_idx, cap_idx, sum_idx = 0, 1, 2
    prev_bracket_cap = 0
    for bracket in brackets:
        if yr_income < bracket[cap_idx]:
            return(bracket[sum_idx] + # tax owed up to prev bracket
                   bracket[rate_idx]*(yr_income-prev_bracket_cap)) # tax owed in this bracket
        prev_bracket_cap = bracket[cap_idx]

def test_unit(units:int=1):
    """
    Creates a Simulator with only 1 monte carlo simulation allowed. 

    Parameters
    ----------
    None

    Returns
    -------
    Simulator
        Instance of the class defined in this file. 

    """
    test_mdl= model.Model()
    
    return Simulator(test_mdl.param_vals, override_dict={'monte_carlo_runs':units})

if __name__ == '__main__':
    #instantiate a Simulator and run at least 1 simulation
    test_simulator = test_unit(units=MONTE_CARLO_RUNS)
    test_simulator.main()
