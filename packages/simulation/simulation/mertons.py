from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MertonsResult:
    stock_allocation: float
    spending_tilt: float  # monthly


def _annual_to_monthly(annual: float) -> float:
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def get_rra_for_all_stocks(
    annual_equity_premium: float, annual_variance: float
) -> float:
    """The RRA that would return 100% equity allocation."""
    return annual_equity_premium / annual_variance


def plain_mertons(
    *,
    annual_bond_return: float,
    annual_equity_premium: float,
    annual_variance_stocks: float,
    rra: float,
    time_preference: float,
    annual_additional_spending_tilt: float,
) -> MertonsResult:
    ep_by_var = annual_equity_premium / annual_variance_stocks
    ep_pow2_by_2var = annual_equity_premium * ep_by_var * 0.5
    c0 = annual_bond_return - time_preference + ep_pow2_by_2var
    c1 = ep_pow2_by_2var

    if math.isinf(rra):
        return MertonsResult(
            stock_allocation=0.0,
            spending_tilt=_annual_to_monthly(annual_additional_spending_tilt),
        )

    one_over_gamma = 1.0 / rra
    stock_allocation = ep_by_var * one_over_gamma
    annual_spending_tilt = (
        one_over_gamma * c0
        + one_over_gamma * one_over_gamma * c1
        + annual_additional_spending_tilt
    )
    return MertonsResult(
        stock_allocation=stock_allocation,
        spending_tilt=_annual_to_monthly(annual_spending_tilt),
    )


def effective_mertons(
    *,
    annual_bond_return: float,
    annual_equity_premium: float,
    annual_variance_stocks: float,
    rra: float,
    time_preference: float,
    annual_additional_spending_tilt: float,
) -> MertonsResult:
    effective_equity_premium = max(0.0, annual_equity_premium)
    rra_for_all_stocks = get_rra_for_all_stocks(
        effective_equity_premium, annual_variance_stocks
    )
    effective_rra = max(rra_for_all_stocks, rra)
    result = plain_mertons(
        annual_bond_return=annual_bond_return,
        annual_equity_premium=effective_equity_premium,
        annual_variance_stocks=annual_variance_stocks,
        rra=effective_rra,
        time_preference=time_preference,
        annual_additional_spending_tilt=annual_additional_spending_tilt,
    )
    return MertonsResult(
        stock_allocation=min(1.0, max(0.0, result.stock_allocation)),
        spending_tilt=result.spending_tilt,
    )
