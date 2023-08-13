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
from app.models.financial.state import State
from app.models.controllers import Controllers


@dataclass
class EconomicData:
    stock_return: float
    bond_return: float
    real_estate_return: float
    inflation: float


@dataclass
class Income(util.FloatRepr):
    job_income: float
    social_security_user: float
    social_security_partner: float


def gen_income() -> Income:
    pass


@dataclass
class Costs(util.FloatRepr):
    spending: float
    kids: float
    income_tax: float
    medicare_tax: float
    ss_tax: float


def gen_costs() -> Costs:
    pass


@dataclass
class NetTransactions(util.FloatRepr):
    income: Income
    costs: Costs
    annuity: float
    portfolio_return: float


def gen_net_transactions() -> NetTransactions:
    gen_income()
    gen_costs()

    def gen_annuity():
        pass

    gen_annuity()

    def gen_portfolio_return():
        pass

    gen_portfolio_return()


@dataclass
class StateChangeComponents:
    allocation: AllocationRatios
    economic_data: EconomicData
    net_transactions: NetTransactions


def gen_state_change_components(
    state: State, controllers: Controllers
) -> StateChangeComponents:
    def gen_economic_data():
        pass

    return StateChangeComponents(
        allocation=controllers.allocation.gen_allocation(state),
        economic_data=gen_economic_data(),
        net_transactions=gen_net_transactions(),
    )
