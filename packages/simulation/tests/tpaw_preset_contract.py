# pinned: tpaw v8 preset outputs for sp500_close + Shiller earnings below.
# regression_prediction / conservative_estimate / one_over_cape / tips_20yr are
# round_p(3)'d by tpaw before feeding presets; historical is NOT rounded (see
# process_market_data_for_presets.rs / process_returns_stats_for_planning.rs).

SP500_CLOSE = 7517.09
TIPS_20YR = 0.026

# pinned: v8 Shiller 10yr average real earnings (Apr 2016–Mar 2026)
EXPECTED_SHILLER_10YR_REAL_EARNINGS = 184.43

# pinned: v8 stock log-variance table endpoints (block_size 1 and 1440)
EXPECTED_STOCK_LOG_VARIANCE_BLOCK_1 = 0.019728282
EXPECTED_STOCK_LOG_VARIANCE_BLOCK_1440 = 0.03258074

EXPECTED_ONE_OVER_CAPE_ROUNDED = 0.025
EXPECTED_REGRESSION_PREDICTION = 0.052
EXPECTED_CONSERVATIVE_ESTIMATE = 0.038
EXPECTED_HISTORICAL_STOCKS = 0.08736731943660461
EXPECTED_HISTORICAL_BONDS = 0.027723000918458578

# Sep 4, 2026 NYSE close — live TPAW guide parity smoke.
SEP4_2026_SP500_CLOSE = 7718.60
SEP4_2026_ONE_OVER_CAPE = 0.024
SEP4_2026_REGRESSION_PREDICTION = 0.052
SEP4_2026_CONSERVATIVE_ESTIMATE = 0.037
