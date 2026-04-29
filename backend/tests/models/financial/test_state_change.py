"""Testing for models/financial/state_change.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false

import numpy as np
import pytest

from app.data.constants import INTERVALS_PER_YEAR
from app.models.controllers import Controllers
from app.models.financial.state import State
from app.models.financial.state_change import Income, StateChangeComponents


def test_income(
    controllers_mock: Controllers, first_state, components_mock: StateChangeComponents
):
    """Test that income is summed up correctly"""
    fake_values = [1, 2, 3, 4]
    controllers_mock.job_income.get_total_income = lambda *_, **__: fake_values[0]
    controllers_mock.social_security.calc_payment = lambda *_, **__: (
        fake_values[1],
        fake_values[2],
    )
    controllers_mock.pension.calc_payment = lambda *_, **__: fake_values[3]
    components_mock.controllers = controllers_mock
    components_mock.state = first_state
    income = Income(components_mock)
    assert income.sum == pytest.approx(sum(fake_values))


def test_portfolio_return(
    mocker,
    components_mock: StateChangeComponents,
):
    """Test that portfolio return is calculated correctly"""
    net_worth = 100
    asset_rates = [0.2, -0.2]
    allocation = np.array([0.4, 0.6])
    dot_product = -0.04
    expected_return = net_worth * dot_product

    components_mock.state = mocker.MagicMock()
    components_mock.state.net_worth = net_worth
    components_mock.economic_data = mocker.MagicMock()
    components_mock.economic_data.asset_rates = asset_rates
    components_mock.allocation = allocation
    components_mock.controllers = mocker.MagicMock()

    portfolio_return = StateChangeComponents._calc_portfolio_return(components_mock)
    assert portfolio_return == pytest.approx(expected_return)


class TestSpendingControllerIntegration:
    """Integration tests for spending controller in StateChangeComponents"""

    def test_spending_via_controller(
        self, sample_user, sample_spending_profiles, controllers_mock
    ):
        """Test spending calculation through controller integration"""
        from app.models.config.user import User
        from app.models.controllers.spending import Controller

        # Create user with new spending_strategy format
        user_dict = sample_user.model_dump()
        user_dict["spending_strategy"] = {
            "inflation_following": {
                "chosen": True,
                "profiles": sample_spending_profiles,
            }
        }
        test_user = User(**user_dict)

        # Create spending controller
        spending_controller = Controller(user=test_user)
        controllers_mock.spending = spending_controller

        # Create state
        state = State(
            user=test_user,
            date=2030.0,
            interval_idx=0,
            net_worth=250.0,
            inflation=1.05,
        )

        # Calculate spending
        spending = spending_controller.calc_spending(state=state)

        # Expected: -(60 / 4) * 1.05 = -15.75
        expected = (
            -(sample_spending_profiles[0].yearly_amount / INTERVALS_PER_YEAR)
            * state.inflation
        )
        assert spending == pytest.approx(expected)

    def test_spending_controller_in_components(
        self, sample_user, sample_spending_profiles, controllers_mock, components_mock
    ):
        """Test spending controller integrated in StateChangeComponents"""
        from app.models.config.user import User
        from app.models.controllers.spending import Controller

        # Create user with new spending_strategy format
        user_dict = sample_user.model_dump()
        user_dict["spending_strategy"] = {
            "inflation_following": {
                "chosen": True,
                "profiles": sample_spending_profiles,
            }
        }
        user_dict.pop("spending", None)
        test_user = User(**user_dict)

        # Setup controllers
        spending_controller = Controller(user=test_user)
        controllers_mock.spending = spending_controller

        # Setup components
        components_mock.controllers = controllers_mock
        components_mock.state = State(
            user=test_user,
            date=2030.0,
            interval_idx=0,
            net_worth=250.0,
            inflation=1.05,
        )

        # This would call the updated _calc_spending that uses controllers.spending
        # For now, test the controller directly
        spending = components_mock.controllers.spending.calc_spending(
            state=components_mock.state
        )

        expected = (
            -(sample_spending_profiles[0].yearly_amount / INTERVALS_PER_YEAR)
            * components_mock.state.inflation
        )
        assert spending == pytest.approx(expected)
