
"""
    First we're making a frame for the data. The frame will only be made once for each set of params (genes)
        Even though it's only made once per params, due to the hyper-volume we'll be testing, still needs to be fast
    Only necessary data is taken from the frame (or maybe the frame is only made of necessary data)
    Monte Carlo is run on the necessary frame to get success rate
    
"""
import datetime as dt
import numpy as np

TODAY = dt.date.today()
TODAY_QUARTER = TODAY.year+((TODAY.month-1)//3)*.25


class Simulator:
    def __init__(self,param_vals):
        self.params = self._clean_data(param_vals)
        self.rows = int((param_vals['Calculate Til'] - TODAY_QUARTER)/.25)
            
    def main(self):
# -------------------------------- VARIABLES -------------------------------- #

    # fixed values regardless
        year_quarter_ls = self._range_len(START=TODAY_QUARTER,LEN=self.rows,INCREMENT=0.25,ADD=True)
        working_qrts = int((self.params["FI Quarter"]-TODAY_QUARTER)/.25)
        FI_qrts = self.rows-working_qrts
        FI_state_ls = [0]*working_qrts +[1]*FI_qrts
        total_income_qrt = self._val("His Total Income",MOD='dollar')+self._val("Her Total Income",MOD='dollar')
        tax_deferred_qrt = self._val("His Tax Deferred",MOD='dollar')+self._val("Her Tax Deferred",MOD='dollar')
        job_income_ls, tax_deferred_ls = [total_income_qrt], [tax_deferred_qrt]
        raise_yr = 1+self._val("Raise (%)",MOD=False)
        # income increases at beginning of each year
        for x in self._range_len(START=((TODAY.month-1)//3)+1,LEN=working_qrts-1,INCREMENT=1,ADD=True):
            if x%4 !=0:
                job_income_ls.append(job_income_ls[-1])
                tax_deferred_ls.append(tax_deferred_ls[-1])
            else:
                job_income_ls.append(job_income_ls[-1]*raise_yr)
                tax_deferred_ls.append(tax_deferred_ls[-1]*raise_yr)
        job_income_ls, tax_deferred_ls = job_income_ls +[0]*FI_qrts,tax_deferred_ls +[0]*FI_qrts

    # varied only due to controlable adjustable parameters
        PensionCol = 10
        HisSSCol = 11
        HerSSCol = 12
        TotalIncomeCol = 13
        TaxCol = 14

        
    # vary with the monte carlo randomness
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

    def _val(self,KEY:str,MOD):
        """MOD='rate' will return (1+r)^(1/4), MOD='dollar' will return d/4, MOD=False will return value"""
        if MOD=="rate":
            return (1+self.params[KEY]) ** (1. / 4)
        elif MOD=='dollar':
            return self.params[KEY] / 4
        elif not MOD:
            return self.params[KEY]
        else:
            raise Exception("invalid MOD")
            
    
    def _range_len(self,START,LEN:int,INCREMENT,MULT=False,ADD=False):
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

param_vals={
    "FI Quarter":   "2024.5",
    "Calculate Til":   "2090",
    "Equity Return (%)":   "0.09499999999999997",
    "Bond Return (%)":   "0.020000000000000018",
    "RE Return (%)":   "0.1100000000000001",
    "International Proportion":   "0.404",
    "Domestic Proportion":   "0.596",
    "RE Ratio":   "0.4",
    "Equity Target":   "1400",
    "Current RE Alloc ($)":   "282",
    "Year @ Kid #1":   "2025",
    "Year @ Kid #2":   "",
    "Year @ Kid #3":   "",
    "Cost of Kid (% Spending)":   "0.12",
    "Monte Carlo Trials":   "1000",
    "Tax (%)":   "0.35",
    "Inflation (%)":   "0.025",
    "Raise (%)":   "0.04",
    "Capital Gains tax (%)":   "0.15",
    "Current CPI":   "276.589",
    "Early SS":   "True",
    "Early Pension":   "True",
    "Pension Cashout":   "False",
    "Cashout Amount":   "64",
    "Current Net Worth ($)":   "1126",
    "Total Spending (Yearly)":   "75.84800000000001",
    "Housing (Monthly)":   "2.597",
    "Groceries (Monthly)":   "0.525",
    "Car (Monthly)":   "0.285",
    "His (Monthly)":   "0.250",
    "Hers (Monthly)":   "0.400",
    "Leisure (Monthly)":   "0.541",
    "Expense Debt (Monthly)":   "0.044",
    "Other (Monthly)":   "0.162",
    "Travel (Yearly)":   "9.300",
    "Giving (Yearly)":   "6.900",
    "Health (Yearly)":   "2.000",
    "Retirement Change (%)":   "-0.14",
    "Equity Mean":   "1.095",
    "Equity Stdev":   ".16",
    "Equity Annual High":   "1.09",
    "Equity Annual Low":   "1.07",
    "Bond Mean":   "1.02",
    "Bond Stdev":   ".025",
    "Bond Annual High":   "1.02",
    "Bond Annual Low":   "1.015",
    "RE Mean":   "1.11",
    "RE Stdev":   ".14",
    "RE Annual High":   "1.12",
    "RE Annual Low":   "1.08",
    "His Age":   "29",
    "His Salary + Bonus":   "195.5",
    "His 401k":   "20.5",
    "His HSA":   "5.3",
    "His Emplr 401k":   "10.25",
    "His Emplr HSA":   "2.0",
    "His Emplr Contributions":   "12.25",
    "His Tax Deferred":   "38.05",
    "His Total Income":   "207.75",
    "Her Age":   "34",
    "Her Salary":   "103.5",
    "Her Pension Costs":   "-9.315",
    "Her Tax Deferred":   "41.0",
    "Her 403b":   "20.5",
    "Her 457b":   "20.5",
    "Her Total Income":   "94.185",
    "Denica Pension":   {
            "2043": ".0116",
            "2044": ".0128",
            "2045": ".0140",
            "2046": ".0152",
            "2047": ".0164",
            "2048": ".0176",
            "2049": ".0188",
            "2050": ".0200",
            "2051": ".0213",
            "2052": ".0227",
            "2053": ".0240",
            "2054": ".0240",
            "2055": ".0240"
        }
    }

if __name__ == '__main__':
    simulator = Simulator(param_vals)
    simulator.main()