from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

import numpy as np

from simulation.market_data.presets_data import (
    empirical_stats,
    load_cape_regression,
)
from simulation.market_data.returns import load_historical_returns


def round3(value: float) -> float:
    # tpaw round_p(3): round half away from zero to 3 decimals.
    return float(Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def one_over_cape(*, sp500_close: float, shiller_10yr_real_earnings: float) -> float:
    return shiller_10yr_real_earnings / sp500_close


def _rolling_12_sum(log_returns: np.ndarray) -> np.ndarray:
    # tpaw periodize_log_returns: overlapping 12-month log-return sums.
    kernel = np.ones(12, dtype=np.float64)
    return np.convolve(log_returns, kernel, mode="valid")


def _annualized_non_log_mean(log_returns: np.ndarray) -> float:
    annualized_log = _rolling_12_sum(log_returns)
    return float(np.mean(np.expm1(annualized_log)))


def shift_correction(
    *,
    unadjusted_annual_non_log_mean: float,
    series_log_mean: float,
    log_volatility_scale: float,
) -> float:
    # tpaw: the block-size rescaling correction, scaled quadratically by the
    # log-volatility scale.
    return (
        math.log1p(unadjusted_annual_non_log_mean) / 12.0 - series_log_mean
    ) * log_volatility_scale**2


def adjust_log_returns(
    *,
    log_returns: np.ndarray,
    target_annual_non_log: float,
    unadjusted_annual_non_log_mean: float,
    log_volatility_scale: float,
) -> np.ndarray:
    # tpaw adjust_log_returns: shift the series so the *block-bootstrapped*
    # annualized non-log mean matches the target (the per-block table mean is the
    # bootstrap's own mean; the whole-series annualized mean matches only when
    # the table mean equals the series mean). Deviations scale by the
    # log-volatility scale. The series mean is computed once and reused.
    series_log_mean = float(np.mean(log_returns))
    correction = shift_correction(
        unadjusted_annual_non_log_mean=unadjusted_annual_non_log_mean,
        series_log_mean=series_log_mean,
        log_volatility_scale=log_volatility_scale,
    )
    target_monthly_log_mean = math.log1p(target_annual_non_log) / 12.0 - correction
    return (
        target_monthly_log_mean + (log_returns - series_log_mean) * log_volatility_scale
    )


def _shift_correction(log_returns: np.ndarray) -> float:
    # block_size=None, scale=1.0 (the preset-menu correction).
    return shift_correction(
        unadjusted_annual_non_log_mean=historical_annual_return(log_returns),
        series_log_mean=float(np.mean(log_returns)),
        log_volatility_scale=1.0,
    )


def _annual_non_log_from_annual_log(annual_log_mean: float, correction: float) -> float:
    return math.expm1((annual_log_mean / 12.0 + correction) * 12.0)


@lru_cache(maxsize=1)
def _stock_correction() -> float:
    return _shift_correction(load_historical_returns().stocks_log)


def _regression_predictions_raw(one_over_cape_value: float) -> list[float]:
    coeffs = load_cape_regression()
    correction = _stock_correction()
    x = math.log1p(one_over_cape_value)
    return [
        _annual_non_log_from_annual_log(slope * x + intercept, correction)
        for slope, intercept in coeffs.pairs.values()
    ]


def _regression_prediction_from_raw(predictions: list[float]) -> float:
    return round3(sum(predictions) / len(predictions))


def _conservative_estimate_from_raw(
    one_over_cape_value: float, predictions: list[float]
) -> float:
    pool = sorted([one_over_cape_value, *predictions])
    lowest_four = pool[:4]
    return round3(sum(lowest_four) / len(lowest_four))


def regression_prediction(one_over_cape_value: float) -> float:
    return _regression_prediction_from_raw(
        _regression_predictions_raw(one_over_cape_value)
    )


def conservative_estimate(one_over_cape_value: float) -> float:
    predictions = _regression_predictions_raw(one_over_cape_value)
    return _conservative_estimate_from_raw(one_over_cape_value, predictions)


def historical_annual_return(log_returns: np.ndarray) -> float:
    # tpaw does not round_p(3) the historical preset value (unlike regression/
    # conservative/one_over_cape), so this is intentionally unrounded.
    return _annualized_non_log_mean(log_returns)


@dataclass(frozen=True)
class StockEstimates:
    one_over_cape: float
    regression_prediction: float
    conservative_estimate: float
    historical: float


def stock_estimates(*, sp500_close: float) -> StockEstimates:
    coeffs = load_cape_regression()
    ooc = one_over_cape(
        sp500_close=sp500_close,
        shiller_10yr_real_earnings=coeffs.shiller_10yr_real_earnings,
    )
    predictions = _regression_predictions_raw(ooc)
    return StockEstimates(
        one_over_cape=round3(ooc),
        regression_prediction=_regression_prediction_from_raw(predictions),
        conservative_estimate=_conservative_estimate_from_raw(ooc, predictions),
        historical=historical_annual_return(load_historical_returns().stocks_log),
    )


def historical_bond_return() -> float:
    return historical_annual_return(load_historical_returns().bonds_log)


def stock_log_variance(*, block_size_months: int, volatility_scale: float) -> float:
    return (
        empirical_stats(
            asset="stocks", block_size=block_size_months
        ).annual_log_variance
        * volatility_scale**2
    )
