"""Module for representing financial transformation from one state to another

Classes:    
    StateChangeComponents: Collection of components needed to calculate transition to next state
"""
from dataclasses import dataclass

import numpy as np
from app import util
from app.models.financial.taxes import Taxes, calc_taxes
from app.data.constants import INTERVALS_PER_YEAR
from app.models.config import Kids, Spending
from app.models.financial.state import State
from app.models.controllers import Controllers


class Income(util.FloatRepr):
    """Income in a given interval

    Attributes:
        job_income (float): Job income
        social_security_user (float): Social security income for user
        social_security_partner (float): Social security income for partner
        pension (float): Pension income
    """

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
    taxes: Taxes

    def __float__(self):
        return float(
            sum(
                [
                    self.spending,
                    self.kids,
                    self.taxes,
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
    income: Income
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
        self.net_transactions = self._gen_net_transactions()

    def _gen_net_transactions(self) -> _NetTransactions:
        income = Income(self._state, self._controllers)
        portfolio_return = self._state.net_worth * np.dot(
            self._economic_data.asset_rates, self._allocation
        )
        costs = self._gen_costs(income, portfolio_return)

        return _NetTransactions(
            income=income,
            portfolio_return=portfolio_return,
            costs=costs,
            annuity=self._controllers.annuity.make_annuity_transaction(
                state=self._state,
                is_working=self._controllers.job_income.is_working(
                    self._state.interval_idx
                ),
                initial_net_transaction=income.job_income + costs,
            ),
        )

    def _gen_costs(self, income: Income, portfolio_return: float) -> _Costs:
        spending = _calc_spending(
            state=self._state,
            config=self._state.user.spending,
            is_working=(
                self._controllers.job_income.is_working(self._state.interval_idx)
            ),
        )
        return _Costs(
            spending=spending,
            kids=_calc_cost_of_kids(
                current_date=self._state.date,
                spending=spending,
                config=self._state.user.kids,
            ),
            taxes=calc_taxes(
                total_income=income,
                job_income_controller=self._controllers.job_income,
                state=self._state,
                portfolio_return=portfolio_return,
            ),
        )
