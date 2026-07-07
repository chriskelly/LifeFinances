from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

import numpy as np

from simulation.market_data import load_historical_returns
from simulation.market_data.presets_data import (
    load_cape_regression,
    load_stock_log_variance_by_block,
)


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


def _shift_correction(log_returns: np.ndarray) -> float:
    # block_size=None, scale=1.0 (the preset-menu correction).
    monthly_log_mean = float(np.mean(log_returns))
    annualized_non_log = _annualized_non_log_mean(log_returns)
    return math.log1p(annualized_non_log) / 12.0 - monthly_log_mean


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


def regression_prediction(one_over_cape_value: float) -> float:
    predictions = _regression_predictions_raw(one_over_cape_value)
    return round3(sum(predictions) / len(predictions))


def conservative_estimate(one_over_cape_value: float) -> float:
    pool = sorted(
        [one_over_cape_value, *_regression_predictions_raw(one_over_cape_value)]
    )
    lowest_four = pool[:4]
    return round3(sum(lowest_four) / len(lowest_four))


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
    return StockEstimates(
        one_over_cape=round3(ooc),
        regression_prediction=regression_prediction(ooc),
        conservative_estimate=conservative_estimate(ooc),
        historical=historical_annual_return(load_historical_returns().stocks_log),
    )


def historical_bond_return() -> float:
    return historical_annual_return(load_historical_returns().bonds_log)


def stock_log_variance(*, block_size_months: int, volatility_scale: float) -> float:
    table = load_stock_log_variance_by_block()
    if block_size_months not in table:
        raise ValueError(
            f"no vendored stock log variance for block size {block_size_months} "
            f"(table covers {min(table)}..{max(table)})"
        )
    return table[block_size_months] * volatility_scale**2
