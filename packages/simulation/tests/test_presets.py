import pytest
from simulation.market_data import load_historical_returns
from simulation.market_data.presets_data import (
    REGRESSION_KEYS,
    load_cape_regression,
    load_stock_log_variance_by_block,
)
from simulation.presets import (
    conservative_estimate,
    historical_annual_return,
    one_over_cape,
    regression_prediction,
    round3,
    stock_estimates,
    stock_log_variance,
)

from .tpaw_preset_contract import (
    EXPECTED_CONSERVATIVE_ESTIMATE,
    EXPECTED_HISTORICAL_BONDS,
    EXPECTED_HISTORICAL_STOCKS,
    EXPECTED_ONE_OVER_CAPE_ROUNDED,
    EXPECTED_REGRESSION_PREDICTION,
    SP500_CLOSE,
)

SHILLER = load_cape_regression().shiller_10yr_real_earnings


def test_loaders_feed_preset_math():
    coeffs = load_cape_regression()
    table = load_stock_log_variance_by_block()

    assert list(coeffs.pairs.keys()) == list(REGRESSION_KEYS)
    assert set(table.keys()) == set(range(1, 1441))


def test_one_over_cape_is_earnings_over_price():
    expected = SHILLER / SP500_CLOSE

    assert one_over_cape(
        sp500_close=SP500_CLOSE, shiller_10yr_real_earnings=SHILLER
    ) == (expected)


def test_round3_matches_tpaw_round_p():
    # pinned: half-away-from-zero at 3 dp
    assert round3(0.0225) == EXPECTED_ONE_OVER_CAPE_ROUNDED


@pytest.mark.parametrize(
    ("fn", "expected"),
    [
        (regression_prediction, EXPECTED_REGRESSION_PREDICTION),
        (conservative_estimate, EXPECTED_CONSERVATIVE_ESTIMATE),
    ],
)
def test_stock_presets_match_tpaw_contract(fn, expected):
    ooc = one_over_cape(sp500_close=SP500_CLOSE, shiller_10yr_real_earnings=SHILLER)

    assert fn(ooc) == expected


def test_historical_returns_match_tpaw_contract():
    # tpaw does not round_p(3) the historical preset, so this pins full
    # precision. np.mean/np.convolve summation order can differ by a ULP or
    # two across platforms/BLAS backends, so compare with a tight relative
    # tolerance rather than exact equality.
    returns = load_historical_returns()

    assert historical_annual_return(returns.stocks_log) == pytest.approx(
        EXPECTED_HISTORICAL_STOCKS, rel=1e-12
    )
    assert historical_annual_return(returns.bonds_log) == pytest.approx(
        EXPECTED_HISTORICAL_BONDS, rel=1e-12
    )


def test_stock_estimates_bundle_derives_from_same_inputs():
    ooc = one_over_cape(sp500_close=SP500_CLOSE, shiller_10yr_real_earnings=SHILLER)
    estimates = stock_estimates(sp500_close=SP500_CLOSE)

    assert estimates.one_over_cape == round3(ooc)
    assert estimates.regression_prediction == regression_prediction(ooc)
    assert estimates.conservative_estimate == conservative_estimate(ooc)


def test_stock_log_variance_scales_table_entry():
    block_size = 60
    scale = 2.0
    table = load_stock_log_variance_by_block()

    assert stock_log_variance(block_size_months=block_size, volatility_scale=scale) == (
        table[block_size] * scale**2
    )


def test_stock_log_variance_rejects_unknown_block_size():
    with pytest.raises(ValueError, match="block size"):
        stock_log_variance(block_size_months=99999, volatility_scale=1.0)
