"""Module for representing financial transformation from one state to another

Classes:
    TotalCosts: 
    
    StateChangeComponents:

Methods:
    gen_transformation(state: State): 
"""
from dataclasses import dataclass
from app import util
from app.models.financial.state import State
from app.models.controllers import Controllers


@dataclass
class _Income(util.FloatRepr):
    job_income: float
    social_security_user: float
    social_security_partner: float


def gen_income() -> _Income:
    pass


@dataclass
class _Costs(util.FloatRepr):
    spending: float
    kids: float
    income_tax: float
    medicare_tax: float
    ss_tax: float


def gen_costs() -> _Costs:
    pass


@dataclass
class _NetTransactions(util.FloatRepr):
    income: _Income
    costs: _Costs
    annuity: float
    portfolio_return: float


def gen_net_transactions() -> _NetTransactions:
    gen_income()
    gen_costs()

    def gen_annuity():
        pass

    gen_annuity()

    def gen_portfolio_return():
        pass

    gen_portfolio_return()

    return 1


class StateChangeComponents:
    def __init__(self, state: State, controllers: Controllers):
        self.allocation = controllers.allocation.gen_allocation(state)
        self.economic_data = controllers.economic_data.get_economic_state_data(state)
        self.net_transactions = gen_net_transactions()
