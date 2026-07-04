from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContributionsAndWithdrawals:
    essential: float
    discretionary: float
    general: float
    total: float
    from_savings_rate: float
    balance: float
    insufficient: bool


@dataclass(frozen=True)
class AllocationResult:
    balance: float
    stock_allocation_on_total: float


def _withdraw(balance: float, amount: float) -> tuple[float, float]:
    """Draw `amount` clamped to `balance`. Returns (withdrawn, remaining)."""
    withdrawn = amount if amount < balance else balance
    return withdrawn, balance - withdrawn


def apply_contributions_and_withdrawals(
    *,
    balance_starting: float,
    contributions: float,
    essential: float,
    discretionary: float,
    general: float,
) -> ContributionsAndWithdrawals:
    balance = balance_starting + contributions
    drawn_essential, balance = _withdraw(balance, essential)
    drawn_discretionary, balance = _withdraw(balance, discretionary)
    drawn_general, balance = _withdraw(balance, general)

    total = drawn_essential + drawn_discretionary + drawn_general
    requested = essential + discretionary + general
    from_savings_rate = (total - contributions) / balance_starting
    return ContributionsAndWithdrawals(
        essential=drawn_essential,
        discretionary=drawn_discretionary,
        general=drawn_general,
        total=total,
        from_savings_rate=from_savings_rate,
        balance=balance,
        insufficient=requested > balance_starting + contributions,
    )


def apply_allocation(
    *,
    stock_allocation: float,
    stock_return: float,
    bond_return: float,
    balance: float,
    npv_income_without_current_month: float,
) -> AllocationResult:
    stocks_amount = balance * stock_allocation
    bonds_amount = balance - stocks_amount
    ending_balance = stocks_amount * (1.0 + stock_return) + bonds_amount * (
        1.0 + bond_return
    )
    total_portfolio = balance + npv_income_without_current_month
    stock_on_total = 0.0 if total_portfolio == 0.0 else stocks_amount / total_portfolio
    return AllocationResult(
        balance=ending_balance, stock_allocation_on_total=stock_on_total
    )
