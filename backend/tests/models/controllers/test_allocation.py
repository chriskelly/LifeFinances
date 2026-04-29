"""Testing for models/financials/allocation.py"""

# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false
# pyright: reportOptionalSubscript=false, reportArgumentType=false

import copy
import csv
from pathlib import Path

import numpy as np
import pytest
from pytest_mock.plugin import MockerFixture

from app.data import constants
from app.models.config import (
    AllocationOptions,
    IncomeProfile,
    InflationFollowingConfig,
    NetWorthPivotStrategyConfig,
    Portfolio,
    SpendingProfile,
    SpendingStrategyOptions,
    TotalPortfolioStrategyConfig,
    User,
)
from app.models.controllers.allocation import (
    Controller,
    _FlatAllocationStrategy,
    _NetWorthPivotStrategy,
    _TotalPortfolioStrategy,
)
from app.models.financial.state import State

# Import types from conftest
from tests.conftest import AssetStats


def test_flat_allocation_strategy(
    sample_user: User, first_state: State, assets: AssetStats
):
    """Should return an np.ndarray with the correct ratios"""
    asset_lookup = {
        assets.us_stock.label: 0,
        assets.us_bond.label: 1,
    }
    sample_config = sample_user.portfolio.allocation_strategy.flat
    assert sample_config is not None
    strategy = _FlatAllocationStrategy(config=sample_config, asset_lookup=asset_lookup)
    # Test with controllers=None (optional parameter)
    allocation = strategy.gen_allocation(state=first_state, controllers=None)
    assert isinstance(allocation, np.ndarray)
    assert allocation == pytest.approx([0.6, 0.4])


def test_net_worth_pivot_strategy(first_state: State, assets: AssetStats):
    """Test that the net worth pivot strategy returns the correct ratios

    The strategy should return the under target allocation if the net worth is
    below the target, and a weighted average of the under and over target
    allocations if the net worth is above the target. Target should be adjusted
    for inflation.
    """
    asset_lookup = {
        assets.us_stock.label: 0,
        assets.us_bond.label: 1,
        "10_yr_Treasury": 2,
        assets.tips.label: 3,
    }
    under_target_allocation = np.array([0.8, 0.2, 0, 0])
    under_target_allocation_config = dict(
        zip(asset_lookup.keys(), under_target_allocation, strict=True)
    )
    over_target_allocation = np.array([0.2, 0, 0.4, 0.4])
    over_target_allocation_config = dict(
        zip(asset_lookup.keys(), over_target_allocation, strict=True)
    )
    net_worth_target = 100
    strategy = _NetWorthPivotStrategy(
        config=NetWorthPivotStrategyConfig(
            under_target_allocation=under_target_allocation_config,
            over_target_allocation=over_target_allocation_config,
            net_worth_target=net_worth_target,
        ),
        asset_lookup=asset_lookup,
    )

    first_state.net_worth = net_worth_target * 0.9  # Under target
    assert strategy.gen_allocation(
        state=first_state, controllers=None
    ) == pytest.approx(under_target_allocation)

    first_state.net_worth = net_worth_target  # At target
    assert strategy.gen_allocation(
        state=first_state, controllers=None
    ) == pytest.approx(under_target_allocation)

    first_state.net_worth = net_worth_target * 4  # Over target
    expected_allocation = (0.25 * under_target_allocation) + (
        0.75 * over_target_allocation
    )
    assert strategy.gen_allocation(
        state=first_state, controllers=None
    ) == pytest.approx(expected_allocation)

    first_state.net_worth = net_worth_target * 5
    first_state.inflation = 4  # Over target, with inflation
    expected_allocation = (0.8 * under_target_allocation) + (
        0.2 * over_target_allocation
    )
    assert strategy.gen_allocation(
        state=first_state, controllers=None
    ) == pytest.approx(expected_allocation)


def test_strategy_interface_accepts_optional_controllers(
    sample_user: User, first_state: State, assets: AssetStats
):
    """Test that all strategies accept optional controllers parameter"""
    asset_lookup = {assets.us_stock.label: 0, assets.us_bond.label: 1}

    # Flat strategy should work with or without controllers
    flat_config = sample_user.portfolio.allocation_strategy.flat
    assert flat_config is not None
    flat_strategy = _FlatAllocationStrategy(
        config=flat_config, asset_lookup=asset_lookup
    )
    allocation1 = flat_strategy.gen_allocation(state=first_state, controllers=None)
    assert isinstance(allocation1, np.ndarray)

    # Net worth pivot strategy should work with or without controllers
    net_worth_config = NetWorthPivotStrategyConfig(
        under_target_allocation={assets.us_stock.label: 1.0},
        over_target_allocation={assets.us_bond.label: 1.0},
        net_worth_target=100000,
    )
    net_worth_strategy = _NetWorthPivotStrategy(
        config=net_worth_config, asset_lookup=asset_lookup
    )
    allocation2 = net_worth_strategy.gen_allocation(state=first_state, controllers=None)
    assert isinstance(allocation2, np.ndarray)


def test_controller_dispatch_total_portfolio_strategy(
    sample_config_data, first_state: State, assets: AssetStats
):
    """Test that Controller correctly dispatches to total_portfolio strategy"""
    # Modify sample config to choose total_portfolio instead of flat
    sample_config_data["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False
    sample_config_data["portfolio"]["allocation_strategy"]["total_portfolio"][
        "chosen"
    ] = True

    user = User(**sample_config_data)
    asset_lookup = {
        assets.tips.label: 0,
        assets.us_stock.label: 1,
        assets.us_bond.label: 2,
        assets.intl_ex_us_stock.label: 3,
    }

    # Create controller and verify it instantiates _TotalPortfolioStrategy
    controller = Controller(user=user, asset_lookup=asset_lookup)
    assert controller._strategy is not None
    assert isinstance(controller._strategy, _TotalPortfolioStrategy)

    # Verify gen_allocation requires controllers for total_portfolio
    with pytest.raises(ValueError, match="controllers parameter is required"):
        controller.gen_allocation(state=first_state, controllers=None)


class TestTotalPortfolioStrategy:
    @pytest.fixture(autouse=True)
    def _patch_statistics_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        test_statistics_csv_path: Path,
    ):
        """Automatically point STATISTICS_PATH at the test CSV for all tests in this class."""
        monkeypatch.setattr(constants, "STATISTICS_PATH", test_statistics_csv_path)

    @pytest.fixture
    def basic_strategy_config(self, assets: AssetStats):
        return TotalPortfolioStrategyConfig(
            enabled=True,
            chosen=True,
            low_risk_allocation={assets.tips.label: 1.0},
            high_risk_allocation={assets.us_stock.label: 1.0},
            RRA=2.0,
        )

    @pytest.fixture
    def basic_strategy(
        self,
        basic_strategy_config: TotalPortfolioStrategyConfig,
        assets: AssetStats,
    ) -> _TotalPortfolioStrategy:
        """Create a _TotalPortfolioStrategy instance for testing"""
        config = basic_strategy_config
        asset_lookup = {assets.tips.label: 0, assets.us_stock.label: 1}
        return _TotalPortfolioStrategy(config=config, asset_lookup=asset_lookup)

    @pytest.fixture
    def basic_user(self, basic_strategy_config: TotalPortfolioStrategyConfig) -> User:
        """Create a minimal user config for total portfolio strategy testing"""
        return User(
            age=30,
            spending_strategy=SpendingStrategyOptions(
                inflation_following=InflationFollowingConfig(
                    chosen=True,
                    profiles=[SpendingProfile(yearly_amount=80)],
                )
            ),
            income_profiles=[
                IncomeProfile(starting_income=100, last_date=constants.TODAY_YR_QT + 20)
            ],
            portfolio=Portfolio(
                current_net_worth=1000,
                allocation_strategy=AllocationOptions(
                    total_portfolio=basic_strategy_config,
                ),
            ),
        )

    @pytest.fixture
    def user_with_savings_no_income(self, basic_user: User) -> User:
        """Create a minimal user config for total portfolio strategy testing"""
        user = copy.deepcopy(basic_user)
        user.income_profiles = None
        return user

    @pytest.fixture
    def user_with_income_no_savings(self, basic_user: User) -> User:
        """Create a minimal user config for total portfolio strategy testing"""
        user = copy.deepcopy(basic_user)
        user.portfolio.current_net_worth = 0
        return user

    @pytest.fixture
    def controller_factory(self, mocker: MockerFixture):
        """Factory that creates Controllers wired to the provided user."""
        from app.models.controllers import Controllers
        from app.models.controllers.economic_data import EconomicStateData
        from app.models.controllers.future_income import (
            Controller as FutureIncomeController,
        )
        from app.models.controllers.job_income import Controller as JobIncomeController
        from app.models.controllers.spending import Controller as SpendingController

        def _create_controllers(
            user: User,
            *,
            social_security: object | None = None,
            pension: object | None = None,
            inflation_values: list[float] | None = None,
        ):
            job_income_controller = JobIncomeController(user)
            spending_controller = SpendingController(user=user)

            # Create zero-returning mocks if not provided (matches production where
            # controllers always exist but may return zero income)
            if social_security is None:
                social_security = mocker.MagicMock()
                social_security.calc_payment = mocker.Mock(return_value=(0.0, 0.0))

            if pension is None:
                pension = mocker.MagicMock()
                pension.calc_payment = mocker.Mock(return_value=0.0)

            # Mock economic_data controller with inflation values
            mock_economic_data = mocker.MagicMock()
            if inflation_values is None:
                # Default: no inflation (1.0 for all intervals)
                inflation_values = [1.0] * user.intervals_per_trial

            def _get_economic_state_data(interval_idx: int) -> EconomicStateData:
                return EconomicStateData(
                    asset_rates=np.array([]),  # Not used in allocation precomputation
                    inflation=inflation_values[interval_idx],
                    asset_lookup={},  # Not used in allocation precomputation
                )

            mock_economic_data.get_economic_state_data = mocker.Mock(
                side_effect=_get_economic_state_data
            )

            # Create real FutureIncomeController for realistic test scenarios
            future_income_controller = FutureIncomeController(
                user=user,
                job_income_controller=job_income_controller,
                social_security_controller=social_security,
                pension_controller=pension,
                economic_data_controller=mock_economic_data,
            )

            controllers = mocker.MagicMock(spec=Controllers)
            controllers.job_income = job_income_controller
            controllers.social_security = social_security
            controllers.pension = pension
            controllers.economic_data = mock_economic_data
            controllers.future_income = future_income_controller
            controllers.spending = spending_controller
            return controllers

        return _create_controllers

    # ---- Tests for _TotalPortfolioStrategy.__post_init__() (T018) ----

    def test_post_init_expected_behavior(
        self,
        assets: AssetStats,
        basic_strategy: _TotalPortfolioStrategy,
    ):
        """Test that __post_init__ correctly calculates expected returns"""
        # Expected returns: AverageYield - 1.0
        assert basic_strategy.expected_low_risk_return == pytest.approx(
            assets.tips.expected_return
        )
        assert basic_strategy.expected_high_risk_return == pytest.approx(
            assets.us_stock.expected_return
        )
        assert basic_strategy.expected_high_risk_stdev == pytest.approx(
            assets.us_stock.stdev
        )

    def test_post_init_merton_share(self, assets: AssetStats):
        """Test that __post_init__ correctly calculates Merton Share"""
        high_risk_asset = assets.us_stock
        low_risk_asset = assets.tips
        config = TotalPortfolioStrategyConfig(
            enabled=True,
            low_risk_allocation={low_risk_asset.label: 1.0},
            high_risk_allocation={high_risk_asset.label: 1.0},
            RRA=2.0,
        )
        asset_lookup = {assets.tips.label: 0, assets.us_stock.label: 1}

        strategy = _TotalPortfolioStrategy(config=config, asset_lookup=asset_lookup)

        # Merton Share = (E[high] - E[low]) / (RRA * stdev[high]^2)
        expected_merton_share = (
            high_risk_asset.expected_return - low_risk_asset.expected_return
        ) / (2.0 * (high_risk_asset.stdev**2))
        assert strategy.merton_share == pytest.approx(expected_merton_share)
        assert 0.0 <= strategy.merton_share <= 1.0  # Should be capped

    def test_post_init_weighted_allocation(self, assets: AssetStats):
        """Test that __post_init__ correctly calculates weighted returns for mixed allocations"""

        config = TotalPortfolioStrategyConfig(
            enabled=True,
            low_risk_allocation={assets.tips.label: 0.5, assets.us_bond.label: 0.5},
            high_risk_allocation={assets.us_stock.label: 1.0},
            RRA=2.0,
        )
        asset_lookup = {
            assets.tips.label: 0,
            assets.us_bond.label: 1,
            assets.us_stock.label: 2,
        }

        strategy = _TotalPortfolioStrategy(config=config, asset_lookup=asset_lookup)

        # Weighted low risk: 0.5 * tips_return + 0.5 * us_bond_return
        expected_low_risk = (
            0.5 * assets.tips.expected_return + 0.5 * assets.us_bond.expected_return
        )
        assert strategy.expected_low_risk_return == pytest.approx(expected_low_risk)
        assert strategy.expected_high_risk_return == pytest.approx(
            assets.us_stock.expected_return
        )

    def test_post_init_missing_asset(self, assets: AssetStats):
        """Test that __post_init__ raises ValueError for missing asset statistics"""

        MISSING_ASSET_LABEL = "REIT"  # REIT is valid but not in test CSV

        # Use a valid asset name (from real CSV) that's not in test CSV
        # REIT exists in real CSV but not in our test one
        config = TotalPortfolioStrategyConfig(
            enabled=True,
            low_risk_allocation={MISSING_ASSET_LABEL: 1.0},
            high_risk_allocation={assets.us_stock.label: 1.0},
            RRA=2.0,
        )
        asset_lookup = {MISSING_ASSET_LABEL: 0, assets.us_stock.label: 1}

        with pytest.raises(ValueError, match="Missing asset statistics.*REIT"):
            _TotalPortfolioStrategy(config=config, asset_lookup=asset_lookup)

    def test_post_init_merton_share_division_by_zero(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        assets: AssetStats,
        basic_strategy_config: TotalPortfolioStrategyConfig,
    ):
        """Test that __post_init__ handles division by zero in Merton Share (zero stdev)"""
        # Create CSV with zero stdev asset for this specific test
        csv_path = tmp_path / "zero_stdev_statistics.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["VariableLabel", "AverageYield", "StdDeviation"])
            writer.writerow(["Inflation", "1.12", "0.18"])
            writer.writerow([assets.us_stock.label, "1.08", "0.0"])  # Zero stdev
            writer.writerow([assets.tips.label, "1.04", "0.06"])

        original_path = constants.STATISTICS_PATH
        monkeypatch.setattr(constants, "STATISTICS_PATH", csv_path)

        try:
            config = basic_strategy_config
            asset_lookup = {assets.tips.label: 0, assets.us_stock.label: 1}

            strategy = _TotalPortfolioStrategy(config=config, asset_lookup=asset_lookup)

            # Should handle division by zero gracefully
            assert strategy._merton_division_by_zero is True
            assert strategy.merton_share == 0.0
        finally:
            monkeypatch.setattr(constants, "STATISTICS_PATH", original_path)

    def test_post_init_merton_share_capping(self, assets: AssetStats):
        """Test that Merton Share is capped to [0, 1]"""
        # Test negative Merton Share (should be capped to 0)
        config_negative = TotalPortfolioStrategyConfig(
            enabled=True,
            low_risk_allocation={
                assets.us_stock.label: 1.0
            },  # Higher return than high risk
            high_risk_allocation={assets.tips.label: 1.0},  # Lower return
            RRA=2.0,
        )
        asset_lookup = {assets.tips.label: 0, assets.us_stock.label: 1}

        strategy_negative = _TotalPortfolioStrategy(
            config=config_negative, asset_lookup=asset_lookup
        )
        assert assets.us_stock.expected_return > assets.tips.expected_return
        # Merton Share = (tips_return - us_stock_return) / (2.0 * us_stock_stdev^2) = negative, should cap to 0
        assert strategy_negative.merton_share == 0.0

        # Test Merton Share > 1 (should be capped to 1)
        # Use very high return difference and low RRA
        config_high = TotalPortfolioStrategyConfig(
            enabled=True,
            low_risk_allocation={assets.tips.label: 1.0},
            high_risk_allocation={assets.us_stock.label: 1.0},
            RRA=0.1,  # Very low RRA
        )

        strategy_high = _TotalPortfolioStrategy(
            config=config_high, asset_lookup=asset_lookup
        )
        # Merton Share = (us_stock_return - tips_return) / (0.1 * us_stock_stdev^2) should be > 1, should cap to 1
        assert strategy_high.merton_share == pytest.approx(1.0)

    # ---- Tests for _TotalPortfolioStrategy.gen_allocation() edge cases (T019) ----

    def test_gen_allocation_zero_savings(
        self,
        basic_strategy: _TotalPortfolioStrategy,
        controller_factory,
        user_with_income_no_savings: User,
    ):
        """Test gen_allocation with zero savings returns low-risk allocation"""
        state = State(
            user=user_with_income_no_savings,
            date=constants.TODAY_YR_QT,
            interval_idx=0,
            net_worth=user_with_income_no_savings.portfolio.current_net_worth,
            inflation=1.0,
        )

        controllers = controller_factory(user_with_income_no_savings)
        allocation = basic_strategy.gen_allocation(state=state, controllers=controllers)

        # With zero savings, should return low-risk allocation
        assert allocation == pytest.approx(basic_strategy.low_risk_allocation)
        assert allocation.sum() == pytest.approx(1.0)

    def test_gen_allocation_negative_savings(
        self,
        basic_strategy: _TotalPortfolioStrategy,
        controller_factory,
        basic_user: User,
    ):
        """Test gen_allocation with negative savings returns low-risk allocation"""
        basic_user.portfolio.current_net_worth = -1000.0
        state = State(
            user=basic_user,
            date=constants.TODAY_YR_QT,
            interval_idx=0,
            net_worth=basic_user.portfolio.current_net_worth,
            inflation=1.0,
        )

        controllers = controller_factory(basic_user)
        allocation = basic_strategy.gen_allocation(state=state, controllers=controllers)

        # With negative savings and no future income, should return low-risk allocation
        assert allocation == pytest.approx(basic_strategy.low_risk_allocation)
        assert allocation.sum() == pytest.approx(1.0)

    def test_gen_allocation_zero_total_portfolio(
        self,
        basic_strategy: _TotalPortfolioStrategy,
        controller_factory,
        basic_user: User,
    ):
        """Test gen_allocation when total portfolio is zero or negative returns low-risk allocation"""
        # Set total portfolio (net worth + future income) to zero
        basic_user.portfolio.current_net_worth = 0.0
        basic_user.income_profiles = None

        state = State(
            user=basic_user,
            date=constants.TODAY_YR_QT,
            interval_idx=0,
            net_worth=basic_user.portfolio.current_net_worth,
            inflation=1.0,
        )

        controllers = controller_factory(basic_user)
        allocation = basic_strategy.gen_allocation(state=state, controllers=controllers)

        # Zero total portfolio should return low-risk allocation
        assert allocation == pytest.approx(basic_strategy.low_risk_allocation)

    def test_gen_allocation_very_high_future_income(
        self,
        basic_strategy: _TotalPortfolioStrategy,
        controller_factory,
        basic_user: User,
    ):
        """Test gen_allocation with very high future income relative to savings returns high-risk allocation"""
        # Set future income to very high
        basic_user.income_profiles[0].starting_income = 1000000
        basic_user.portfolio.current_net_worth = 10

        state = State(
            user=basic_user,
            date=constants.TODAY_YR_QT,
            interval_idx=0,
            net_worth=basic_user.portfolio.current_net_worth,
            inflation=1.0,
        )

        controllers = controller_factory(basic_user)
        allocation = basic_strategy.gen_allocation(state=state, controllers=controllers)

        # With very high future income, should allocate more to high-risk
        # (savings_high_risk_ratio should be high)
        assert allocation == pytest.approx(basic_strategy.high_risk_allocation)
        assert allocation.sum() == pytest.approx(1.0)

    def test_gen_allocation_very_high_savings(
        self,
        basic_strategy: _TotalPortfolioStrategy,
        controller_factory,
        user_with_savings_no_income: User,
    ):
        """Test gen_allocation with high savings relative to future income returns merton share allocation"""
        state = State(
            user=user_with_savings_no_income,
            date=constants.TODAY_YR_QT,
            interval_idx=0,
            net_worth=user_with_savings_no_income.portfolio.current_net_worth,
            inflation=1.0,
        )

        controllers = controller_factory(user_with_savings_no_income)
        allocation = basic_strategy.gen_allocation(state=state, controllers=controllers)

        # With very high savings and no future income, allocation should be
        # based on Merton Share directly (real FutureIncomeController returns zero for no income)
        expected_merton_share = (
            basic_strategy.expected_high_risk_return
            - basic_strategy.expected_low_risk_return
        ) / (2.0 * (basic_strategy.expected_high_risk_stdev**2))
        assert allocation[1] == pytest.approx(expected_merton_share)
        assert allocation.sum() == pytest.approx(1.0)

    def test_gen_allocation_division_by_zero_fallback(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        basic_user: User,
        controller_factory,
        assets: AssetStats,
    ):
        """Test that gen_allocation falls back to low-risk when Merton Share had division by zero"""
        # Create CSV with zero stdev for this specific test
        csv_path = tmp_path / "zero_stdev_statistics.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["VariableLabel", "AverageYield", "StdDeviation"])
            writer.writerow(["Inflation", "1.12", "0.18"])
            writer.writerow([assets.us_stock.label, "1.08", "0.0"])  # Zero stdev
            writer.writerow([assets.tips.label, "1.04", "0.06"])

        original_path = constants.STATISTICS_PATH
        monkeypatch.setattr(constants, "STATISTICS_PATH", csv_path)

        try:
            config = basic_user.portfolio.allocation_strategy.total_portfolio
            assert config is not None
            asset_lookup = {assets.tips.label: 0, assets.us_stock.label: 1}
            strategy = _TotalPortfolioStrategy(config=config, asset_lookup=asset_lookup)

            state = State(
                user=basic_user,
                date=constants.TODAY_YR_QT,
                interval_idx=0,
                net_worth=basic_user.portfolio.current_net_worth,
                inflation=1.0,
            )

            controllers = controller_factory(basic_user)
            allocation = strategy.gen_allocation(state=state, controllers=controllers)

            # Should return low-risk allocation when division by zero occurred
            assert allocation == pytest.approx(strategy.low_risk_allocation)
            assert allocation.sum() == pytest.approx(1.0)
        finally:
            monkeypatch.setattr(constants, "STATISTICS_PATH", original_path)

    # ---- Integration test (T021) ----

    def test_integration_controller(
        self,
        sample_config_data,
        mocker: MockerFixture,
        assets: AssetStats,
    ):
        """Integration test: Controller.gen_allocation() with total_portfolio strategy"""
        # Modify sample config to choose total_portfolio (assumes default allocation strategy is flat)
        sample_config_data["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False
        sample_config_data["portfolio"]["allocation_strategy"]["total_portfolio"][
            "chosen"
        ] = True

        user = User(**sample_config_data)
        asset_lookup = {
            assets.tips.label: 0,
            assets.us_stock.label: 1,
            assets.us_bond.label: 2,
            assets.intl_ex_us_stock.label: 3,
        }

        # Create real controllers (mock economic_data since it requires EconomicEngine)
        from app.models.controllers import Controllers
        from app.models.controllers.allocation import (
            Controller as AllocationController,
        )
        from app.models.controllers.annuity import Controller as AnnuityController
        from app.models.controllers.economic_data import EconomicStateData
        from app.models.controllers.future_income import (
            Controller as FutureIncomeController,
        )
        from app.models.controllers.job_income import (
            Controller as JobIncomeController,
        )
        from app.models.controllers.pension import Controller as PensionController
        from app.models.controllers.social_security import (
            Controller as SocialSecurityController,
        )
        from app.models.controllers.spending import Controller as SpendingController

        allocation_controller = AllocationController(
            user=user, asset_lookup=asset_lookup
        )
        job_income_controller = JobIncomeController(user)
        social_security_controller = SocialSecurityController(
            user, job_income_controller
        )
        pension_controller = PensionController(user)
        annuity_controller = AnnuityController(user)
        spending_controller = SpendingController(user=user)

        # Mock economic_data controller with inflation values
        mock_economic_data = mocker.MagicMock()
        # Default: no inflation (1.0 for all intervals)
        inflation_values = [1.0] * user.intervals_per_trial

        def _get_economic_state_data(interval_idx: int) -> EconomicStateData:
            return EconomicStateData(
                asset_rates=np.array([]),  # Not used in allocation precomputation
                inflation=inflation_values[interval_idx],
                asset_lookup={},  # Not used in allocation precomputation
            )

        mock_economic_data.get_economic_state_data = mocker.Mock(
            side_effect=_get_economic_state_data
        )

        # Create real future_income controller
        future_income_controller = FutureIncomeController(
            user=user,
            job_income_controller=job_income_controller,
            social_security_controller=social_security_controller,
            pension_controller=pension_controller,
            economic_data_controller=mock_economic_data,
        )

        controllers = Controllers(
            allocation=allocation_controller,
            economic_data=mock_economic_data,
            job_income=job_income_controller,
            social_security=social_security_controller,
            pension=pension_controller,
            annuity=annuity_controller,
            future_income=future_income_controller,
            spending=spending_controller,
        )

        # Create state
        from app.models.financial.state import gen_first_state

        state = gen_first_state(user)

        # Generate allocation
        allocation = controllers.allocation.gen_allocation(
            state=state, controllers=controllers
        )

        # Verify allocation properties
        assert isinstance(allocation, np.ndarray)
        assert allocation.sum() == pytest.approx(1.0)
        assert np.all(allocation >= 0)  # All allocations non-negative
        assert len(allocation) == len(asset_lookup)

        # Verify allocation respects RRA (with Merton Share = 0.8, should have
        # significant high-risk allocation if total portfolio is positive)
        if state.net_worth > 0:
            # Should have some allocation to both high and low risk assets
            assert allocation[0] > 0 or allocation[1] > 0  # TIPS or US_Stock
