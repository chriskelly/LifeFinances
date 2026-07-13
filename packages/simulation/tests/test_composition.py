import numpy as np
from simulation.composition import prorate_net_income_by_source, wealth_by_income_source
from simulation.npv import backward_npv_including_current


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


def test_wealth_by_source_sums_to_combined_income_wealth():
    months = 4
    gross_job = np.array([100.0, 100.0, 0.0, 0.0], dtype=np.float64)
    gross_ss = np.array([0.0, 0.0, 50.0, 50.0], dtype=np.float64)
    zeros = np.zeros(months, dtype=np.float64)
    taxes = np.array([-20.0, -20.0, -5.0, -5.0], dtype=np.float64)
    monthly_inflation = 0.0
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

    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=zeros,
        gross_manual=zeros,
        taxes=taxes,
    )
    combined_nominal = sum(nets[k] for k in nets)
    deflator = (1.0 + monthly_inflation) ** np.arange(months, dtype=np.float64)
    combined_real = combined_nominal / deflator
    expected_total = backward_npv_including_current(
        combined_real, one_over_1_plus_r=one_over
    )

    actual_total = wealth.job + wealth.social_security + wealth.pension + wealth.manual
    np.testing.assert_allclose(actual_total, expected_total)
