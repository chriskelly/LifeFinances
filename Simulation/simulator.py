
"""
    First we're making a frame for the data. The frame will only be made once for each set of params (genes)
        Even though it's only made once per params, due to the hyper-volume we'll be testing, still needs to be fast
    Only necessary data is taken from the frame (or maybe the frame is only made of necessary data)
    Monte Carlo is run on the necessary frame to get success rate
    
    Yearly v Monthly?? Quarterly a good compromise? Want to represent rebalancing more accurately. 
"""
import datetime as dt
import numpy as np

TODAY = dt.date.today()
TODAY_QUARTER = TODAY.year+((TODAY.month-1)//3)*.25


class Simulator:
    def __init__(self,param_vals):
        self.params = param_vals
        self.rows = int((float(param_vals['Calculate Til']) - TODAY_QUARTER)/.25)
            
    def main(self):
# -------------------------------- VARIABLES -------------------------------- #

    # fixed columns
        year_quarter = list(np.linspace(start=TODAY_QUARTER,stop=TODAY_QUARTER+self.rows*.25,num=self.rows,endpoint=False))
        years_till_FI = 1
        FICol = 3
        his_income = 7
        HerIncomeCol = 8
        TaxDeferedCol = 9
        PensionCol = 10
        HisSSCol = 11
        HerSSCol = 12
        TotalIncomeCol = 13
        TaxCol = 14


        
    # simulated columns
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
