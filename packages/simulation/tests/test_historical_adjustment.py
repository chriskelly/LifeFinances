import math

import pytest
from core.models import DEFAULT_BLOCK_SIZE_MONTHS
from simulation.market_data.presets_data import load_empirical_stats_by_block
from simulation.market_data.returns import load_historical_returns
from simulation.presets import (
    adjust_log_returns,
    historical_annual_return,
    shift_correction,
)


def test_adjust_log_returns_targets_annualized_non_log_mean():
    series = load_historical_returns().stocks_log
    target = 0.05
    block_mean = load_empirical_stats_by_block("stocks")[DEFAULT_BLOCK_SIZE_MONTHS].mean

    adjusted = adjust_log_returns(
        log_returns=series,
        target_annual_non_log=target,
        unadjusted_annual_non_log_mean=block_mean,
        log_volatility_scale=1.0,
    )

    assert historical_annual_return(adjusted) == pytest.approx(target, abs=1e-3)


def test_adjust_log_returns_scales_standard_deviation():
    series = load_historical_returns().stocks_log
    scale = 0.5
    block_mean = load_empirical_stats_by_block("stocks")[DEFAULT_BLOCK_SIZE_MONTHS].mean

    adjusted = adjust_log_returns(
        log_returns=series,
        target_annual_non_log=0.05,
        unadjusted_annual_non_log_mean=block_mean,
        log_volatility_scale=scale,
    )

    assert adjusted.std(ddof=1) == pytest.approx(series.std(ddof=1) * scale)


def test_shift_correction_scales_quadratically_with_log_volatility_scale():
    unadjusted_annual_non_log_mean = 0.087
    series_log_mean = 0.006

    base = shift_correction(
        unadjusted_annual_non_log_mean=unadjusted_annual_non_log_mean,
        series_log_mean=series_log_mean,
        log_volatility_scale=1.0,
    )
    scaled = shift_correction(
        unadjusted_annual_non_log_mean=unadjusted_annual_non_log_mean,
        series_log_mean=series_log_mean,
        log_volatility_scale=2.0,
    )

    assert scaled == pytest.approx(base * 4.0)


def test_adjust_log_returns_correction_uses_block_mean_not_series_mean():
    series = load_historical_returns().stocks_log
    target = 0.05
    block_mean = load_empirical_stats_by_block("stocks")[
        1
    ].mean  # differs from series mean
    series_log_mean = float(series.mean())
    series_annual_non_log = historical_annual_return(series)
    # guards the test's discriminating power: block mean != series annual non-log mean
    assert abs(block_mean - series_annual_non_log) > 1e-3

    adjusted = adjust_log_returns(
        log_returns=series,
        target_annual_non_log=target,
        unadjusted_annual_non_log_mean=block_mean,
        log_volatility_scale=1.0,
    )
    expected_log_mean = math.log1p(target) / 12.0 - shift_correction(
        unadjusted_annual_non_log_mean=block_mean,
        series_log_mean=series_log_mean,
        log_volatility_scale=1.0,
    )

    assert adjusted.mean() == pytest.approx(expected_log_mean)
