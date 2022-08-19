
class Annuity:
    def __init__(self,interest_rate_qt,payout_rate_qt,time_ls:list):
        self.interest_rate = interest_rate_qt
        self.payout_rate = payout_rate_qt
        self.time_ls = time_ls
        self.transactions = [0 for _ in time_ls] #net contibutions/withdrawals
        self.balances = []
    
    def contribute(self,amount,date):
        self.transactions[self.time_ls.index(date)] += amount
        self._update_balances()
    
    def _update_balances(self):
        self.balances = []
        for i, amount in enumerate(self.transactions):
            self.balances.append(amount)
            if i != 0: 
                self.balances[i] += self.balances[i-1] * self.interest_rate
            
    def annuitize(self,date):
        self.payments = self.balances[self.time_ls.index(date)] * self.payout_rate
    
    def income(self,time):
        pass
    
    
if __name__ == '__main__':
    annuity = Annuity(interest_rate_qt=1.001,payout_rate_qt=0.01,time_ls=[2022,2022.25,2022.5,2022.75,2023,2023.25,2023.5,2023.75])
    annuity.contribute(100,2022)
    annuity.contribute(100,2022.5)
    annuity.annuitize(2023.5)
    debug=True