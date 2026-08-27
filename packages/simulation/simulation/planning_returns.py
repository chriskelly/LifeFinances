from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from core.models import Plan, PlanningReturnsConfig

from simulation.market_data import (
    SP500Resolved,
    TreasuryYieldsResolved,
    load_historical_returns,
    resolve_latest_sp500_close,
    resolve_treasury_real_yields,
)
from simulation.presets import (
    StockEstimates,
    historical_annual_return,
    historical_bond_return,
    round3,
    stock_estimates,
    stock_log_variance,
)

TWENTY_YEAR_TENOR = "20"


class SP500Resolver(Protocol):
    def __call__(
        self,
        *,
        today: date | None = None,
        allow_refresh: bool = False,
        now: datetime | None = None,
        api_key: str | None = None,
    ) -> SP500Resolved: ...


class TreasuryResolver(Protocol):
    def __call__(
        self,
        *,
        today: date | None = None,
        allow_refresh: bool = False,
        now: datetime | None = None,
    ) -> TreasuryYieldsResolved: ...


@dataclass(frozen=True)
class PlanningReturns:
    annual_stocks: float
    annual_bonds: float
    annual_stock_log_variance: float
    sp500: SP500Resolved | None = None
    treasury: TreasuryYieldsResolved | None = None


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


class _LazyMarketFeeds:
    """Memoize full SP500/Treasury resolver objects; unused feeds stay None."""

    def __init__(
        self,
        *,
        sp500_resolver: SP500Resolver,
        treasury_resolver: TreasuryResolver,
        today: date,
        allow_refresh: bool,
        now: datetime | None,
        eod_api_key: str | None,
    ) -> None:
        self._sp500_resolver = sp500_resolver
        self._treasury_resolver = treasury_resolver
        self._today = today
        self._allow_refresh = allow_refresh
        self._now = now
        self._eod_api_key = eod_api_key
        # Public: `resolve_planning_returns` reads these directly after
        # resolution to report which feeds a preset actually consumed.
        self.sp500: SP500Resolved | None = None
        self.treasury: TreasuryYieldsResolved | None = None
        self._stock_estimates_cache: StockEstimates | None = None

    def sp500_resolved(self) -> SP500Resolved:
        if self.sp500 is None:
            self.sp500 = self._sp500_resolver(
                today=self._today,
                allow_refresh=self._allow_refresh,
                now=self._now,
                api_key=self._eod_api_key,
            )
        return self.sp500

    def treasury_resolved(self) -> TreasuryYieldsResolved:
        if self.treasury is None:
            self.treasury = self._treasury_resolver(
                today=self._today,
                allow_refresh=self._allow_refresh,
                now=self._now,
            )
        return self.treasury

    def tips_20yr(self) -> float:
        # tpaw rounds the 20yr TIPS yield to 3dp (source_rounded.bond_rates) before
        # it feeds any preset.
        return round3(self.treasury_resolved().yields[TWENTY_YEAR_TENOR])

    def stocks_from_base(self, base: str) -> float:
        if base == "historical":
            return historical_annual_return(load_historical_returns().stocks_log)
        if self._stock_estimates_cache is None:
            self._stock_estimates_cache = stock_estimates(
                sp500_close=self.sp500_resolved().close
            )
        estimates = self._stock_estimates_cache
        return {
            "regression_prediction": estimates.regression_prediction,
            "conservative_estimate": estimates.conservative_estimate,
            "one_over_cape": estimates.one_over_cape,
        }[base]

    def bonds_from_base(self, base: str) -> float:
        if base == "historical":
            return historical_bond_return()
        return self.tips_20yr()


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
    feeds = _LazyMarketFeeds(
        sp500_resolver=sp500_resolver,
        treasury_resolver=treasury_resolver,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        eod_api_key=eod_api_key,
    )

    annual_stocks, annual_bonds = _resolve_preset_returns(
        config,
        stocks_from_base=feeds.stocks_from_base,
        bonds_from_base=feeds.bonds_from_base,
        tips_20yr=feeds.tips_20yr,
    )

    variance = stock_log_variance(
        block_size_months=plan.sampling.block_size_months,
        volatility_scale=float(config.stock_volatility_scale),
    )
    return PlanningReturns(
        annual_stocks=annual_stocks,
        annual_bonds=annual_bonds,
        annual_stock_log_variance=variance,
        sp500=feeds.sp500,
        treasury=feeds.treasury,
    )
