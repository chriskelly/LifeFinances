"""Testing for models/taxes.py
"""
# pylint:disable=missing-class-docstring,protected-access,redefined-outer-name
# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import pytest
from app.data.constants import INTERVALS_PER_YEAR
from app.data.taxes import DISCOUNT_ON_PENSION_TAX, SOCIAL_SECURITY_TAX_RATE
from app.models.config import IncomeProfile, User
from app.models.financial.state import State

from app.util import max_earnings_extrapolator
from app.models.financial.taxes import (
    _TaxRules,
    _bracket_math,
    _calc_income_taxes,
    _social_security_tax,
    calc_taxes,
)
from app.models.controllers.job_income import Controller as JobIncomeController


class TestCalcTaxes:
    medicare_tax_rate = 0.1
    income_tax = -1
    social_security_tax = -2

    @pytest.fixture(autouse=True)
    def monkeypatch(self, monkeypatch: pytest.MonkeyPatch):
        """Patch functions and constants for testing"""
        monkeypatch.setattr(
            "app.models.financial.taxes._calc_income_taxes", lambda **_: self.income_tax
        )
        monkeypatch.setattr(
            "app.models.financial.taxes.MEDICARE_TAX_RATE", self.medicare_tax_rate
        )
        monkeypatch.setattr(
            "app.models.financial.taxes._social_security_tax",
            lambda *_: self.social_security_tax,
        )

    def test_calc_taxes(self, mocker, sample_user: User, first_state: State):
        """Test that the Taxes object is calculated correctly"""
        portfolio_return = 10
        portfolio_tax_rate = 0.2

        mock_income = mocker.MagicMock()
        mock_income.job_income = 25
        mock_income.social_security_user = 0
        mock_income.social_security_partner = 0
        mock_income.pension = 0

        sample_user.income_profiles = [
            IncomeProfile(
                starting_income=mock_income.job_income * INTERVALS_PER_YEAR,
                last_date=3000,
            ),
        ]
        sample_user.partner = None
        controller = JobIncomeController(sample_user)

        first_state.user.portfolio.tax_rate = portfolio_tax_rate

        taxes = calc_taxes(
            total_income=mock_income,
            job_income_controller=controller,
            state=first_state,
            portfolio_return=portfolio_return,
        )
        expected_pension_tax = (1 - DISCOUNT_ON_PENSION_TAX) * self.income_tax
        assert taxes.income == pytest.approx(self.income_tax + expected_pension_tax)
        assert taxes.medicare == pytest.approx(
            mock_income.job_income * -self.medicare_tax_rate
        )
        assert taxes.social_security == pytest.approx(self.social_security_tax)
        assert taxes.portfolio == pytest.approx(portfolio_return * -portfolio_tax_rate)


class TestCalcIncomeTaxes:
    @pytest.fixture(autouse=True)
    def monkeypatch_bracket_math(self, monkeypatch: pytest.MonkeyPatch):
        """Bracket math will return -1 for each time it's called."""
        monkeypatch.setattr("app.models.financial.taxes._bracket_math", lambda **_: -1)

    def test_when_taxable_income_is_zero(self, first_state: State):
        """
        Test that the function returns 0 when the taxable income is 0.
        """
        assert _calc_income_taxes(interval_income=0, state=first_state) == 0

    def test_when_taxable_income_is_positive(self, first_state: State):
        """
        Test that the function returns the tax owed when the taxable income
        is positive. The tax owed is the sum of the federal and state taxes,
        each of which will be the value set by the monkeypatch.
        """
        assert (
            _calc_income_taxes(interval_income=100, state=first_state)
            == -2 / INTERVALS_PER_YEAR
        )

    def test_when_no_residence_state_declared(self, first_state: State):
        """
        Test that the bracket_math is only called once (for federal taxes,
        not on state brackets) when no residence state is declared.
        """
        first_state.user.state = None
        assert (
            _calc_income_taxes(interval_income=100, state=first_state)
            == -1 / INTERVALS_PER_YEAR
        )


class TestTaxRules:
    federal_standard_deduction_mock = [1, 2]
    federal_bracket_rates_mock = [
        [[0.1, 1, 0], [0.2, 2, 0.1]],
        [[0.1, 2, 0], [0.2, 4, 0.2]],
    ]
    state_standard_deduction_mock = {"California": [10, 20]}
    state_bracket_rates_mock = {
        "California": [[[0.1, 10, 0], [0.2, 20, 1]], [[0.1, 20, 0], [0.2, 40, 2]]]
    }
    single_index = 0
    married_index = 1

    def compare_brackets(self, brackets_1, brackets_2):
        """
        Compare two brackets to see if they are equal.
        """
        for i, bracket in enumerate(brackets_1):
            assert bracket == pytest.approx(brackets_2[i])

    @pytest.fixture(autouse=True)
    def monkeypatch_tax_constants(self, monkeypatch: pytest.MonkeyPatch):
        """Fix constants for testing."""
        monkeypatch.setattr(
            "app.models.financial.taxes.FED_STD_DEDUCTION",
            self.federal_standard_deduction_mock,
        )
        monkeypatch.setattr(
            "app.models.financial.taxes.FED_BRACKET_RATES",
            self.federal_bracket_rates_mock,
        )
        monkeypatch.setattr(
            "app.models.financial.taxes.STATE_STD_DEDUCTION",
            self.state_standard_deduction_mock,
        )
        monkeypatch.setattr(
            "app.models.financial.taxes.STATE_BRACKET_RATES",
            self.state_bracket_rates_mock,
        )

    def test_when_residence_state_is_none(self, sample_user: User):
        """
        Test that the function returns the correct TaxRules object when the user's
        residence state is None.
        """
        sample_user.state = None
        tax_rules = _TaxRules(sample_user)
        self.compare_brackets(
            tax_rules.federal_bracket_rates,
            self.federal_bracket_rates_mock[self.married_index],
        )
        assert tax_rules.state_bracket_rates is None
        assert tax_rules.federal_standard_deduction == pytest.approx(
            self.federal_standard_deduction_mock[self.married_index]
        )
        assert tax_rules.state_standard_deduction == 0

    def test_when_residence_state_is_not_none(self, sample_user: User):
        """
        Test that the function returns the correct TaxRules object when the user's
        residence state is not None.
        """
        sample_user.state = "California"
        tax_rules = _TaxRules(sample_user)
        self.compare_brackets(
            tax_rules.federal_bracket_rates,
            self.federal_bracket_rates_mock[self.married_index],
        )
        self.compare_brackets(
            tax_rules.state_bracket_rates,
            self.state_bracket_rates_mock["California"][self.married_index],
        )
        assert tax_rules.federal_standard_deduction == pytest.approx(
            self.federal_standard_deduction_mock[self.married_index]
        )
        assert tax_rules.state_standard_deduction == pytest.approx(
            self.state_standard_deduction_mock["California"][self.married_index]
        )

    def test_when_not_married(self, sample_user: User):
        """
        Test that the function returns the correct TaxRules object when the user is married.
        """
        sample_user.state = "California"
        sample_user.partner = None
        tax_rules = _TaxRules(sample_user)
        self.compare_brackets(
            tax_rules.federal_bracket_rates,
            self.federal_bracket_rates_mock[self.single_index],
        )
        self.compare_brackets(
            tax_rules.state_bracket_rates,
            self.state_bracket_rates_mock["California"][self.single_index],
        )
        assert tax_rules.federal_standard_deduction == pytest.approx(
            self.federal_standard_deduction_mock[self.single_index]
        )
        assert tax_rules.state_standard_deduction == pytest.approx(
            self.state_standard_deduction_mock["California"][self.single_index]
        )


class TestBracketMath:
    brackets = [[0.1, 100, 0], [0.2, 200, 10], [0.3, 300, 30]]

    def use_set_brackets(self, yearly_income: float):
        """
        Use the brackets defined in the class and return the tax owed
        for the given yearly income.
        """
        return _bracket_math(brackets=self.brackets, yearly_income=yearly_income)

    def test_when_yearly_income_is_zero(self):
        """
        Test that the function returns 0 when the yearly income is 0.
        """
        assert self.use_set_brackets(yearly_income=0) == 0

    def test_when_yearly_income_is_less_than_first_bracket_cap(self):
        """
        Test that the function returns the tax owed in the first bracket
        when the yearly income is less than the cap of the first bracket.
        """
        assert self.use_set_brackets(yearly_income=50) == pytest.approx(-5)

    def test_when_yearly_income_is_over_first_bracket(self):
        """
        Test that the function returns the tax owed in the current bracket
        when the yearly income is within a bracket.
        """
        assert self.use_set_brackets(yearly_income=150) == pytest.approx(-20)

    def test_when_yearly_income_is_under_last_bracket_cap(self):
        """
        Test that the function returns the tax owed up to the previous bracket
        plus the tax owed in the current bracket when the yearly income
        is greater than a bracket cap.
        """
        assert self.use_set_brackets(yearly_income=250) == pytest.approx(-45)

    def test_when_yearly_income_is_greater_than_highest_bracket_cap(self):
        """
        Test that the function raises a ValueError when the yearly income
        is greater than the highest bracket cap.
        """
        with pytest.raises(ValueError):
            self.use_set_brackets(yearly_income=400)


class TestSocialSecurityTax:
    def patch_incomes(
        self, monkeypatch: pytest.MonkeyPatch, user_income: float, partner_income: float
    ):
        """
        Patch the user and partner incomes for testing purposes.

        Args:
            monkeypatch (pytest.MonkeyPatch): The pytest monkeypatch fixture.
            user_income (float): The user's income to patch.
            partner_income (float): The partner's income to patch.
        """
        monkeypatch.setattr(
            "app.models.controllers.job_income.Controller.get_user_income",
            lambda *_: user_income,
        )
        monkeypatch.setattr(
            "app.models.controllers.job_income.Controller.get_partner_income",
            lambda *_: partner_income,
        )

    def test_when_less_than_max_earnings(
        self, monkeypatch, sample_user: User, first_state: State
    ):
        """
        Test that the social security tax is calculated correctly
        when the income of both the user and their partner
        are less than the maximum earnings allowed.
        """
        max_earnings = max_earnings_extrapolator(first_state.date)
        user_income = partner_income = max_earnings - 10
        self.patch_incomes(
            monkeypatch=monkeypatch,
            user_income=user_income,
            partner_income=partner_income,
        )
        tax = _social_security_tax(
            controller=JobIncomeController(sample_user), state=first_state
        )
        assert tax == pytest.approx(
            -SOCIAL_SECURITY_TAX_RATE * (user_income + partner_income)
        )

    def test_when_user_higher_than_max_earnings(
        self, monkeypatch, sample_user: User, first_state: State
    ):
        """
        Test that the social security tax is calculated correctly
        when the user's income is higher than the maximum earnings allowed.
        """
        max_earnings = max_earnings_extrapolator(first_state.date)
        user_income = max_earnings + 10
        partner_income = max_earnings - 10
        self.patch_incomes(
            monkeypatch=monkeypatch,
            user_income=user_income,
            partner_income=partner_income,
        )
        tax = _social_security_tax(
            controller=JobIncomeController(sample_user), state=first_state
        )
        assert tax == pytest.approx(
            -SOCIAL_SECURITY_TAX_RATE * (max_earnings + partner_income)
        )

    def test_when_partner_higher_than_max_earnings(
        self, monkeypatch, sample_user: User, first_state: State
    ):
        """
        Test case to verify that the social security tax is calculated correctly
        when the partner's income is higher than the maximum earnings allowed.
        """
        max_earnings = max_earnings_extrapolator(first_state.date)
        user_income = max_earnings - 10
        partner_income = max_earnings + 10
        self.patch_incomes(
            monkeypatch=monkeypatch,
            user_income=user_income,
            partner_income=partner_income,
        )
        tax = _social_security_tax(
            controller=JobIncomeController(sample_user), state=first_state
        )
        assert tax == pytest.approx(
            -SOCIAL_SECURITY_TAX_RATE * (user_income + max_earnings)
        )
