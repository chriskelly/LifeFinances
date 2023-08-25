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
        (
            self.social_security_user,
            self.social_security_partner,
        ) = controllers.social_security.calc_payment(state)

    def __float__(self):
        return float(
            sum(
                [
                    self.job_income,
                    self.social_security_user,
                    self.social_security_partner,
                ]
            )
        )


@dataclass
class _Costs(util.FloatRepr):
    spending: float = 1
    kids: float = 1
    income_tax: float = 1
    medicare_tax: float = 1
    ss_tax: float = 1

    def __float__(self):
        return float(
            sum(
                [
                    self.spending,
                    self.kids,
                    self.income_tax,
                    self.medicare_tax,
                    self.ss_tax,
                ]
            )
        )


def gen_costs() -> _Costs:
    pass


@dataclass
class _NetTransactions(util.FloatRepr):
    income: _Income
    costs: _Costs = 1
    annuity: int = 1
    portfolio_return: float = 1

    def __float__(self):
        return float(
            sum([self.income, self.costs, self.annuity, self.portfolio_return])
        )


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
            income=_Income(state, controllers),
        )
