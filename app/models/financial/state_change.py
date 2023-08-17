"""Module for representing financial transformation from one state to another

Classes:
    TotalCosts: 
    
    StateChangeComponents:

Methods:
    gen_transformation(state: State): 
"""
from dataclasses import dataclass
from app import util
from app.models.controllers.allocation import AllocationRatios
from app.models.controllers.economic_data import EconomicStateData
from app.models.financial.state import State
from app.models.controllers import Controllers


class _Income(util.FloatRepr):
    def __init__(self, state: State, controllers: Controllers):
        self.job_income = controllers.job_income.get_total_income(state.interval_idx)
        self.social_security_user = 1
        self.social_security_partner = 1

    def __float__(self):
        return (
            self.job_income + self.social_security_user + self.social_security_partner
        )


@dataclass
class _Costs(util.FloatRepr):
    spending: float
    kids: float
    income_tax: float
    medicare_tax: float
    ss_tax: float


def gen_costs() -> _Costs:
    pass


class _NetTransactions(util.FloatRepr):
    def __init__(
        self,
        state: State,
        allocation: AllocationRatios,
        economic_data: EconomicStateData,
        controllers: Controllers,
    ):
        self.income = _Income(state, controllers)
        self.costs = 1
        self.annuity = 1
        self.portfolio_return = 1

    def __float__(self):
        return self.income + self.costs + self.annuity + self.portfolio_return


class StateChangeComponents:
    """Collection of components needed to calculate transition to next state.

    Attributes:
        allocation (AllocationRatios): Allocation of assets in provided state

        economic_data (EconomicStateData): Returns and inflation data

        net_transactions (NetTransactions):
    """

    def __init__(self, state: State, controllers: Controllers):
        self.allocation = controllers.allocation.gen_allocation(state)
        self.economic_data = controllers.economic_data.get_economic_state_data(state)
        self.net_transactions = _NetTransactions(
            state, self.allocation, self.economic_data, controllers
        )
