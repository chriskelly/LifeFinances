"""Module for representing financial transformation from one state to another

Classes:    
    StateChangeComponents: Collection of components needed to calculate transition to next state
"""
from dataclasses import dataclass

import numpy as np
from app import util
from app.models.financial.state import State
from app.models.controllers import Controllers


class _Income(util.FloatRepr):
    def __init__(self, state: State, controllers: Controllers):
        self.job_income = controllers.job_income.get_total_income(state.interval_idx)
        (
            self.social_security_user,
            self.social_security_partner,
        ) = controllers.social_security.calc_payment(state)
        self.pension = controllers.pension.calc_payment(state)

    def __float__(self):
        return float(
            sum(
                [
                    self.job_income,
                    self.social_security_user,
                    self.social_security_partner,
                    self.pension,
                ]
            )
        )


@dataclass
class _Costs(util.FloatRepr):
    spending: float = -1
    kids: float = -1
    income_tax: float = -1
    medicare_tax: float = -1
    ss_tax: float = -1

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
    portfolio_return: float
    costs: _Costs
    annuity: float

    def __float__(self):
        return float(
            sum([self.income, self.portfolio_return, self.costs, self.annuity])
        )


class StateChangeComponents:
    """Collection of components needed to calculate transition to next state.

    Attributes:
        allocation (AllocationRatios): Allocation of assets in provided state

        economic_data (EconomicStateData): Returns and inflation data

        net_transactions (NetTransactions): Income, portfolio return, costs, & annuity
    """

    def __init__(self, state: State, controllers: Controllers):
        self._state = state
        self._controllers = controllers
        self.allocation = controllers.allocation.gen_allocation(state)
        self.economic_data = controllers.economic_data.get_economic_state_data(state)

        income = _Income(state, controllers)
        costs = _Costs()
        annuity = controllers.annuity.make_annuity_transaction(
            state=state,
            job_income_controller=controllers.job_income,
            initial_net_transaction=income + costs,
        )
        portfolio_return = state.net_worth * np.dot(
            self.economic_data.asset_rates, self.allocation.assets
        )

        self.net_transactions = _NetTransactions(
            income=income,
            portfolio_return=portfolio_return,
            costs=costs,
            annuity=annuity,
        )
