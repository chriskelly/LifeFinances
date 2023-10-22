"""Module for representing financial transformation from one state to another

Classes:    
    StateChangeComponents: Collection of components needed to calculate transition to next state
"""
from dataclasses import dataclass

import numpy as np
from app import util
from app.data.constants import INTERVALS_PER_YEAR
from app.models.config import Kids, Spending
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
    spending: float
    kids: float
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


def _calc_spending(state: State, config: Spending, is_working: bool) -> float:
    base_amount = -config.yearly_amount / INTERVALS_PER_YEAR * state.inflation
    if not is_working:
        base_amount *= 1 + config.retirement_change
    return base_amount


def _calc_cost_of_kids(current_date: float, spending: float, config: Kids) -> float:
    """Calculate the cost of children

    Args:
        current_date (float): date of state
        spending (float): base spending in current state
        config (Kids)

    Returns:
        float: cost of children for this interval
    """
    if config is None:
        return 0
    current_kids = [
        year
        for year in config.birth_years
        if current_date - config.years_of_support < year <= current_date
    ]
    return len(current_kids) * spending * config.fraction_of_spending


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

    Args:
        state (State): current state
        controllers (Controllers)

    Attributes:
        net_transactions (NetTransactions): Income, portfolio return, costs, & annuity
    """

    def __init__(self, state: State, controllers: Controllers):
        self._state = state
        self._controllers = controllers
        self._allocation = controllers.allocation.gen_allocation(state)
        self._economic_data = controllers.economic_data.get_economic_state_data(
            state.interval_idx
        )

        income = _Income(state, controllers)
        spending = _calc_spending(
            state=state,
            config=state.user.spending,
            is_working=(controllers.job_income.is_working(state.interval_idx)),
        )
        costs = _Costs(
            spending=spending,
            kids=_calc_cost_of_kids(
                current_date=state.date, spending=spending, config=state.user.kids
            ),
        )
        annuity = controllers.annuity.make_annuity_transaction(
            state=state,
            is_working=controllers.job_income.is_working(state.interval_idx),
            initial_net_transaction=income.job_income + costs,
        )
        portfolio_return = state.net_worth * np.dot(
            self._economic_data.asset_rates, self._allocation
        )

        self.net_transactions = _NetTransactions(
            income=income,
            portfolio_return=portfolio_return,
            costs=costs,
            annuity=annuity,
        )
