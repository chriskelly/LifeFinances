from data import constants as const 

class Annuity:
    def __init__(self):
        self.interest_yield = const.ANNUITY_INT_YIELD ** (1/4)
        self.payout_rate = const.ANNUITY_PAYOUT_RATE/4
        self.prev_transaction_row = 0
        self.balance = 0
        self.annuitized = False
    
    def contribute(self,amount:float,row:int):
        """Contribute to the balance of the annuity

        Args:
            amount (float): Amount to be contributed
            row (int): date_ls index of contribution

        Yields:
            no return: Annuity's balance is updated for interest and contribution
        """
        self.balance *= self.interest_yield ** (row - self.prev_transaction_row) # Update balance for interest gained. Interest yield will be 1 when annuitized.
        self.prev_transaction_row = row
        self.balance += amount
            
    def annuitize(self,row:int):
        """Annuitize this annuity

        Args:
            row (int): date_ls index

        Yields:
            no return: Balance is updated for interest gained. No interest gained after this point
        """
        self.balance *= self.interest_yield ** (row - self.prev_transaction_row) # add interest for last time
        self.annuitized = True
        self.interest_yield = 1 # After annuitization, balance does not grow anymore except for contributions.
    
    def take_payment(self) -> float:
        """Request payment from annuity

        Returns:
            float: If annuitized: Balance * Payout Rate; else: 0
        """
        if self.annuitized:
            return self.balance * self.payout_rate
        else:
            return 0
    
    
"""if __name__ == '__main__':
    annuity = Annuity(interest_yield_qt=1.001,payout_rate_qt=0.01,date_ls=[2022,2022.25,2022.5,2022.75,2023,2023.25,2023.5,2023.75])
    annuity.contribute(100,2022)
    annuity.contribute(100,2022.5)
    #annuity.annuitize(2023.5)
    print(annuity.take_payment(2023.75))
    debug=True
    """