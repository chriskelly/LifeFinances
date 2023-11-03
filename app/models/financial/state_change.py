"""Module for representing financial transformation from one state to another

Classes:    
    StateChangeComponents: Collection of components needed to calculate transition to next state
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from app.models.financial.taxes import Taxes, calc_taxes
from app.data.constants import INTERVALS_PER_YEAR
from app.models.financial.state import State
from app.models.controllers import Controllers

# pylint: disable=redefined-builtin


class Income:
    """Income in a given interval

    Attributes:
        job_income (float): Job income
        social_security_user (float): Social security income for user
        social_security_partner (float): Social security income for partner
        pension (float): Pension income
        sum (float): Sum of all income
    """

    def __init__(self, components: StateChangeComponents):
        controllers = components.controllers
        state = components.state

        self.job_income = controllers.job_income.get_total_income(state.interval_idx)
        (
            self.social_security_user,
            self.social_security_partner,
        ) = controllers.social_security.calc_payment(state)
        self.pension = controllers.pension.calc_payment(state)
        self.sum = float(
            self.job_income
            + self.social_security_user
            + self.social_security_partner
            + self.pension
        )


@dataclass
class _Costs:
    spending: float
    kids: float
    taxes: Taxes
    sum: float = None

    def __post_init__(self):
        self.sum = self.spending + self.kids + self.taxes.sum


@dataclass
class _NetTransactions:
    income: Income
    portfolio_return: float
    costs: _Costs
    annuity: float
    sum: float = None

    def __post_init__(self):
        self.sum = (
            self.income.sum + self.portfolio_return + self.costs.sum + self.annuity
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
        self.state = state
        self.controllers = controllers
        self.allocation = controllers.allocation.gen_allocation(state)
        self.economic_data = controllers.economic_data.get_economic_state_data(
            state.interval_idx
        )

        self.net_transactions = StateChangeComponents._gen_net_transactions(
            components=self
        )

    @staticmethod
    def _gen_net_transactions(components: StateChangeComponents) -> _NetTransactions:
        income = Income(components)
        portfolio_return = StateChangeComponents._calc_portfolio_return(components)
        costs = StateChangeComponents._gen_costs(
            components=components, income=income, portfolio_return=portfolio_return
        )

        return _NetTransactions(
            income=income,
            portfolio_return=portfolio_return,
            costs=costs,
            annuity=components.controllers.annuity.make_annuity_transaction(
                state=components.state,
                is_working=components.controllers.job_income.is_working(
                    components.state.interval_idx
                ),
                initial_net_transaction=income.job_income + costs.sum,
            ),
        )

    @staticmethod
    def _calc_portfolio_return(components: StateChangeComponents) -> float:
        return components.state.net_worth * np.dot(
            components.economic_data.asset_rates, components.allocation
        )

    @staticmethod
    def _gen_costs(
        components: StateChangeComponents, income: Income, portfolio_return: float
    ) -> _Costs:
        spending = StateChangeComponents._calc_spending(components)
        return _Costs(
            spending=spending,
            kids=StateChangeComponents._calc_cost_of_kids(
                components=components,
                spending=spending,
            ),
            taxes=calc_taxes(
                total_income=income,
                job_income_controller=components.controllers.job_income,
                state=components.state,
                portfolio_return=portfolio_return,
            ),
        )

    @staticmethod
    def _calc_spending(components: StateChangeComponents) -> float:
        config = components.state.user.spending
        inflation = components.state.inflation
        is_working = components.controllers.job_income.is_working(
            components.state.interval_idx
        )

        base_amount = -config.yearly_amount / INTERVALS_PER_YEAR * inflation
        if not is_working:
            base_amount *= 1 + config.retirement_change
        return base_amount

    @staticmethod
    def _calc_cost_of_kids(components: StateChangeComponents, spending: float) -> float:
        """Calculate the cost of children

        Returns:
            float: cost of children for this interval
        """
        current_date = components.state.date
        config = components.state.user.kids

        if config is None:
            return 0
        current_kids = [
            year
            for year in config.birth_years
            if current_date - config.years_of_support < year <= current_date
        ]
        return len(current_kids) * spending * config.fraction_of_spending
