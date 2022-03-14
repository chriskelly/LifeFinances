class InvestmentType:
    def __init__(self, cash_flow_rate, liquid, price_appreciation=0):
        self.cash_flow_rate = cash_flow_rate
        self.price_appreciation = price_appreciation  # applies only to public equity investments
        self.liquid = liquid


class Investment:
    def __init__(self, init_balance, investment_type):
        self.balance = init_balance
        self.cash_flow_rate = investment_type.cash_flow_rate
        self.liquid = investment_type.liquid
        self.price_appreciation = investment_type.price_appreciation  # applies only to public equity investments
        self.additional_dist = 0  # a distribution from private equity or a re-finance from RE

    def grow(self):
        distribution = self.balance * self.cash_flow_rate + self.additional_dist
        appreciation = self.balance * self.price_appreciation
        self.balance += distribution + appreciation
        return distribution
