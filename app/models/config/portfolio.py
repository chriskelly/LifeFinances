"""Portfolio configuration classes"""

import csv
import math

from pydantic import BaseModel, Field, model_validator

from app.data import constants
from app.models.config.strategy import StrategyConfig, StrategyOptions

with open(constants.STATISTICS_PATH, encoding="utf-8") as file:
    reader = csv.reader(file)
    next(reader)  # Skip the first row
    ALLOWED_ASSETS = {row[0] for row in reader}
    ALLOWED_ASSETS.discard("Inflation")


class AnnuityConfig(BaseModel):
    """
    Attributes
        net_worth_target (float): If net worth falls below this value, the annuity will trigger

        contribution_rate (float): The percentage of net income that will be
        contributed to the annuity
    """

    net_worth_target: float = Field(
        json_schema_extra={
            "ui": {
                "label": "Net Worth Target",
                "tooltip": "Net worth threshold below which annuity purchase is triggered",
                "section": "Portfolio",
                "min_value": 0,
            }
        }
    )
    contribution_rate: float = Field(
        json_schema_extra={
            "ui": {
                "label": "Contribution Rate",
                "tooltip": "Percentage of net income contributed to annuity (e.g., 0.1 = 10%)",
                "section": "Portfolio",
                "min_value": 0,
                "max_value": 1,
            }
        }
    )


def _allocation_sums_to_1(allocation: dict[str, float]):
    """Restrict allocation to sum to 1 if provided"""
    if allocation and not math.isclose(1, sum(allocation.values())):
        raise ValueError("flat strategy allocation must sum to 1")


def _allocation_options_valid(allocation_options: dict[str, float]):
    """All assets must be allowed in allocation options"""
    for asset in allocation_options.keys():
        if asset not in ALLOWED_ASSETS:
            raise ValueError(f"{asset} is not allowed in allocation options")


def _validate_allocation(allocation: dict[str, float]):
    """Validate allocation if provided"""
    _allocation_sums_to_1(allocation)
    _allocation_options_valid(allocation)


class FlatAllocationStrategyConfig(StrategyConfig):
    """
    Attributes
        allocation (dict[str, float])
    """

    allocation: dict[str, float] = Field(
        json_schema_extra={
            "ui": {
                "label": "Asset Allocation",
                "tooltip": "Fixed asset allocation percentages (must sum to 1.0)",
                "section": "Portfolio",
            }
        }
    )

    @model_validator(mode="after")
    def validate_allocation(self):
        """Validate allocation"""
        _validate_allocation(self.allocation)
        return self


class NetWorthPivotStrategyConfig(StrategyConfig):
    """
    Attributes
        net_worth_target (float): Also referred to as equity target
    """

    net_worth_target: float = Field(
        json_schema_extra={
            "ui": {
                "label": "Net Worth Pivot Target",
                "tooltip": "Net worth threshold for switching between allocation strategies",
                "section": "Portfolio",
                "min_value": 0,
            }
        }
    )
    under_target_allocation: dict[str, float] = Field(
        json_schema_extra={
            "ui": {
                "label": "Under Target Allocation",
                "tooltip": "Asset allocation when net worth is below target",
                "section": "Portfolio",
            }
        }
    )
    over_target_allocation: dict[str, float] = Field(
        json_schema_extra={
            "ui": {
                "label": "Over Target Allocation",
                "tooltip": "Asset allocation when net worth is above target",
                "section": "Portfolio",
            }
        }
    )

    @model_validator(mode="after")
    def net_worth_target_greater_or_equal_to_0(self):
        """Restrict net worth target to be greater or equal to 0 if provided"""
        if self.net_worth_target and self.net_worth_target < 0:
            raise ValueError("Net worth target must be greater or equal to 0")
        return self

    @model_validator(mode="after")
    def validate_allocations(self):
        """Validate allocations"""
        _validate_allocation(self.under_target_allocation)
        _validate_allocation(self.over_target_allocation)
        return self


class TotalPortfolioStrategyConfig(StrategyConfig):
    """
    Configuration for total portfolio allocation strategy.

    Attributes:
        low_risk_allocation (dict[str, float]): Low-risk/risk-free portion of portfolio allocation
        high_risk_allocation (dict[str, float]): High-risk portion of portfolio allocation
        RRA (float): Relative Risk Aversion parameter (must be positive)
    """

    low_risk_allocation: dict[str, float] = Field(
        default_factory=lambda: {"TIPS": 1.0},
        json_schema_extra={
            "ui": {
                "label": "Low Risk Allocation",
                "tooltip": "Low-risk/risk-free portion of portfolio allocation (must sum to 1.0)",
                "section": "Portfolio",
            }
        },
    )
    high_risk_allocation: dict[str, float] = Field(
        default_factory=lambda: {"US_Stock": 1.0},
        json_schema_extra={
            "ui": {
                "label": "High Risk Allocation",
                "tooltip": "High-risk portion of portfolio allocation (must sum to 1.0)",
                "section": "Portfolio",
            }
        },
    )
    RRA: float = Field(
        default=2.0,
        json_schema_extra={
            "ui": {
                "label": "Relative Risk Aversion",
                "tooltip": "Relative Risk Aversion parameter (must be positive)",
                "section": "Portfolio",
                "min_value": 0.0001,
            }
        },
    )

    @model_validator(mode="after")
    def validate_rra(self):
        """Validate that RRA is positive"""
        if self.RRA <= 0:
            raise ValueError("RRA must be greater than 0")
        return self

    @model_validator(mode="after")
    def validate_allocations(self):
        """Validate both allocations"""
        _validate_allocation(self.low_risk_allocation)
        _validate_allocation(self.high_risk_allocation)
        return self


class AllocationOptions(StrategyOptions):
    """
    Attributes
        flat (FlatAllocationStrategyConfig): Defaults to None

        net_worth_pivot (NetWorthPivotStrategyConfig): Defaults to None

        total_portfolio (TotalPortfolioStrategyConfig): Defaults to None
    """

    flat: FlatAllocationStrategyConfig | None = None
    net_worth_pivot: NetWorthPivotStrategyConfig | None = None
    total_portfolio: TotalPortfolioStrategyConfig | None = None


class Portfolio(BaseModel):
    """
    Attributes
        current_net_worth (float): Defaults to 0

        tax_rate (float): Defaults to 0.1

        annuity (AnnuityConfig): Defaults to None

        allocation_strategy (AllocationOptions)
    """

    current_net_worth: float = Field(
        default=0,
        json_schema_extra={
            "ui": {
                "label": "Current Net Worth",
                "tooltip": "Your current total net worth in dollars",
                "section": "Portfolio",
                "min_value": 0,
            }
        },
    )
    tax_rate: float = Field(
        default=0.1,
        json_schema_extra={
            "ui": {
                "label": "Tax Rate",
                "tooltip": "Portfolio tax rate (default: 0.1 = 10%)",
                "section": "Portfolio",
                "min_value": 0,
                "max_value": 1,
            }
        },
    )
    annuity: AnnuityConfig | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Annuity",
                "tooltip": "Annuity purchase configuration",
                "section": "Portfolio",
            }
        },
    )
    allocation_strategy: AllocationOptions = Field(
        json_schema_extra={
            "ui": {
                "label": "Allocation Strategy",
                "tooltip": "Asset allocation strategy (flat, net-worth pivot, etc.)",
                "section": "Portfolio",
            }
        }
    )
