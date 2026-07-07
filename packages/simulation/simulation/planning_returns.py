from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from core.models import Plan, PlanningReturnsConfig

from simulation.market_data import (
    SP500Resolved,
    TreasuryYieldsResolved,
    load_historical_returns,
    resolve_latest_sp500_close,
    resolve_treasury_real_yields,
)
from simulation.presets import (
    historical_annual_return,
    historical_bond_return,
    round3,
    stock_estimates,
    stock_log_variance,
)

TWENTY_YEAR_TENOR = "20"

SP500Resolver = Callable[..., SP500Resolved]
TreasuryResolver = Callable[..., TreasuryYieldsResolved]


@dataclass(frozen=True)
class PlanningReturns:
    annual_stocks: float
    annual_bonds: float
    annual_stock_log_variance: float


def _validate_fixed_preset_literals(config: PlanningReturnsConfig) -> None:
    # These literals only drive returns under preset == "fixed"; validating them
    # unconditionally would reject plans whose stale/unused fixed literals
    # happen to be invalid while a different preset is actually active.
    if config.preset != "fixed":
        return

    expected_bonds = float(config.expected_annual_return_bonds)
    if 1.0 + expected_bonds <= 0.0:
        raise ValueError(
            "planning expected annual bond return implies total loss or worse"
        )

    expected_stocks = float(config.expected_annual_return_stocks)
    if 1.0 + expected_stocks <= 0.0:
        raise ValueError(
            "planning expected annual stock return implies total loss or worse"
        )


def _resolve_preset_returns(
    config: PlanningReturnsConfig,
    *,
    stocks_from_base: Callable[[str], float],
    bonds_from_base: Callable[[str], float],
    tips_20yr: Callable[[], float],
) -> tuple[float, float]:
    preset = config.preset
    if preset == "fixed":
        return (
            float(config.expected_annual_return_stocks),
            float(config.expected_annual_return_bonds),
        )
    if preset == "historical":
        return (stocks_from_base("historical"), bonds_from_base("historical"))
    if preset == "fixed_equity_premium":
        if config.fixed_equity_premium is None:
            raise ValueError(
                "fixed_equity_premium preset requires fixed_equity_premium"
            )
        annual_bonds = tips_20yr()
        return (annual_bonds + float(config.fixed_equity_premium), annual_bonds)
    if preset == "custom":
        if config.custom_stocks_base is None or config.custom_bonds_base is None:
            raise ValueError("custom preset requires both custom bases")
        return (
            stocks_from_base(config.custom_stocks_base)
            + float(config.custom_stocks_delta),
            bonds_from_base(config.custom_bonds_base)
            + float(config.custom_bonds_delta),
        )

    # regression_prediction / conservative_estimate / one_over_cape -> stock base + 20yr TIPS
    return (stocks_from_base(preset), tips_20yr())


def resolve_planning_returns(
    plan: Plan,
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    eod_api_key: str | None = None,
    sp500_resolver: SP500Resolver = resolve_latest_sp500_close,
    treasury_resolver: TreasuryResolver = resolve_treasury_real_yields,
) -> PlanningReturns:
    config = plan.planning_returns
    today = today or date.today()
    _validate_fixed_preset_literals(config)

    # Lazy + memoized: only hit the (cache/vendored) data once, and only for
    # presets that actually need it.
    _stock_estimates_cache: list = []

    def sp500_close() -> float:
        return sp500_resolver(
            today=today, allow_refresh=allow_refresh, now=now, api_key=eod_api_key
        ).close

    def tips_20yr() -> float:
        # tpaw rounds the 20yr TIPS yield to 3dp (source_rounded.bond_rates) before
        # it feeds any preset.
        raw = treasury_resolver(
            today=today, allow_refresh=allow_refresh, now=now
        ).yields[TWENTY_YEAR_TENOR]
        return round3(raw)

    def _cached_stock_estimates():
        if not _stock_estimates_cache:
            _stock_estimates_cache.append(stock_estimates(sp500_close=sp500_close()))
        return _stock_estimates_cache[0]

    def stocks_from_base(base: str) -> float:
        if base == "historical":
            return historical_annual_return(load_historical_returns().stocks_log)
        estimates = _cached_stock_estimates()
        return {
            "regression_prediction": estimates.regression_prediction,
            "conservative_estimate": estimates.conservative_estimate,
            "one_over_cape": estimates.one_over_cape,
        }[base]

    def bonds_from_base(base: str) -> float:
        if base == "historical":
            return historical_bond_return()
        return tips_20yr()

    annual_stocks, annual_bonds = _resolve_preset_returns(
        config,
        stocks_from_base=stocks_from_base,
        bonds_from_base=bonds_from_base,
        tips_20yr=tips_20yr,
    )

    variance = stock_log_variance(
        block_size_months=plan.sampling.block_size_months,
        volatility_scale=float(config.stock_volatility_scale),
    )
    return PlanningReturns(
        annual_stocks=annual_stocks,
        annual_bonds=annual_bonds,
        annual_stock_log_variance=variance,
    )
