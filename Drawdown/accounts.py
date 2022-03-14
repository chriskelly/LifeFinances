class Account:
    def __init__(self, name, investments, roth=False, roth_basis=0):
        self.name = name
        self.investments = investments
        self.roth = roth
        self.roth_basis = roth_basis

    def balance(self):
        balance = 0
        for investment in self.investments:
            balance += investment.balance
        return balance

    def liquid_balance(self):
        liquid_balance = 0
        for investment in self.investments:
            if investment.liquid:
                liquid_balance += investment.balance
        return liquid_balance
