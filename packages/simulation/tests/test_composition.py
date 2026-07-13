import numpy as np
from simulation.composition import prorate_net_income_by_source


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
