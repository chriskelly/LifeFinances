import numpy as np
from simulation.composition import prorate_net_income_by_source, wealth_by_income_source


def _npv_including_current_closed_form(
    real_series: np.ndarray, *, one_over: float
) -> np.ndarray:
    """Independent expected NPV: sum of each month's real value discounted back.

    Deliberately does NOT call the production `backward_npv_including_current`
    so the reconciliation test verifies composition's discounting rather than
    trivially restating the helper it uses internally.
    """
    months = len(real_series)
    return np.array(
        [
            sum(real_series[k] * one_over ** (k - m) for k in range(m, months))
            for m in range(months)
        ],
        dtype=np.float64,
    )


def test_prorated_nets_sum_to_net_cashflow_when_gross_positive():
    gross_job = np.array([80.0], dtype=np.float64)
    gross_ss = np.array([20.0], dtype=np.float64)
    gross_pension = np.array([0.0], dtype=np.float64)
    gross_manual = np.array([0.0], dtype=np.float64)
    # Domain stores taxes as non-positive.
    taxes = np.array([-10.0], dtype=np.float64)
    total_gross = gross_job + gross_ss + gross_pension + gross_manual
    net_cashflow = total_gross + taxes

    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        taxes=taxes,
    )

    summed = nets["job"] + nets["social_security"] + nets["pension"] + nets["manual"]
    np.testing.assert_allclose(summed, net_cashflow)


def test_proration_zero_gross_month_yields_zero_nets():
    zeros = np.array([0.0], dtype=np.float64)
    taxes = np.array([-5.0], dtype=np.float64)  # residual tax ignored for composition

    nets = prorate_net_income_by_source(
        gross_job=zeros,
        gross_social_security=zeros.copy(),
        gross_pension=zeros.copy(),
        gross_manual=zeros.copy(),
        taxes=taxes,
    )

    for series in nets.values():
        np.testing.assert_allclose(series, zeros)


def test_wealth_by_source_sums_to_independently_discounted_combined_income():
    months = 4
    # total_gross is positive every month, so combined nets == net cashflow and
    # the wealth bands must reconcile with the combined-income NPV.
    gross_job = np.array([100.0, 100.0, 0.0, 0.0], dtype=np.float64)
    gross_ss = np.array([0.0, 0.0, 50.0, 50.0], dtype=np.float64)
    zeros = np.zeros(months, dtype=np.float64)
    taxes = np.array([-20.0, -20.0, -5.0, -5.0], dtype=np.float64)
    monthly_inflation = 0.02  # nonzero so the deflator is actually exercised
    monthly_bond = 0.01
    one_over = 1.0 / (1.0 + monthly_bond)

    wealth = wealth_by_income_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=zeros,
        gross_manual=zeros,
        taxes=taxes,
        monthly_inflation=monthly_inflation,
        monthly_bond_rate=monthly_bond,
    )

    combined_nominal = gross_job + gross_ss + taxes
    deflator = (1.0 + monthly_inflation) ** np.arange(months, dtype=np.float64)
    combined_real = combined_nominal / deflator
    expected_total = _npv_including_current_closed_form(
        combined_real, one_over=one_over
    )

    actual_total = wealth.job + wealth.social_security + wealth.pension + wealth.manual
    np.testing.assert_allclose(actual_total, expected_total)


def test_proration_zero_gross_months_stay_zero_across_horizon():
    # Composition intentionally drops residual taxes when a month has no gross
    # income (spec §7.1): those months contribute nothing to any wealth band.
    months = 3
    zeros = np.zeros(months, dtype=np.float64)
    taxes = np.array([-5.0, -3.0, -1.0], dtype=np.float64)

    nets = prorate_net_income_by_source(
        gross_job=zeros,
        gross_social_security=zeros.copy(),
        gross_pension=zeros.copy(),
        gross_manual=zeros.copy(),
        taxes=taxes,
    )

    for series in nets.values():
        np.testing.assert_allclose(series, zeros)
