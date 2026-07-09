# pinned: tpaw v7 preset outputs for sp500_close + Shiller earnings below.
# regression_prediction / conservative_estimate / one_over_cape / tips_20yr are
# round_p(3)'d by tpaw before feeding presets; historical is NOT rounded (see
# process_market_data_for_presets.rs / process_returns_stats_for_planning.rs).
# See plan reference table.

SP500_CLOSE = 7517.09
TIPS_20YR = 0.026

EXPECTED_ONE_OVER_CAPE_ROUNDED = 0.023
EXPECTED_REGRESSION_PREDICTION = 0.05
EXPECTED_CONSERVATIVE_ESTIMATE = 0.035
EXPECTED_HISTORICAL_STOCKS = 0.08714729363432902
EXPECTED_HISTORICAL_BONDS = 0.0277107658439772
