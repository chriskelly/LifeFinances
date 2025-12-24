"""Spending configuration classes"""

from pydantic import BaseModel, Field, model_validator

from app.models.config.strategy import StrategyConfig, StrategyOptions


class SpendingOptions(StrategyOptions):
    """
    Attributes
        inflation_only (Strategy): Defaults to None

        ceil_floor (CeilFloorStrategy): Defaults to None
    """

    inflation_only: StrategyConfig = StrategyConfig(chosen=True)


class SpendingProfile(BaseModel):
    """
    Attributes
        yearly_amount (float)

        end_date (float)
    """

    yearly_amount: int
    end_date: float | None = None


def _spending_profiles_validation(spending_profiles: list[SpendingProfile]):
    """Spending profiles must be in order and last profile should have no end date"""
    if spending_profiles:
        # Validate that all profiles except the last have end_date set
        for i in range(len(spending_profiles) - 1):
            if spending_profiles[i].end_date is None:
                raise ValueError(
                    "All spending profiles except the last must have an end_date"
                )

        # Validate ordering: compare end_date values for all profiles except the last
        # Since we've already validated that all except the last have end_date,
        # we can compare directly
        if len(spending_profiles) > 1:
            for i in range(1, len(spending_profiles) - 1):
                end_date_i = spending_profiles[i].end_date
                end_date_prev = spending_profiles[i - 1].end_date
                if end_date_i is not None and end_date_prev is not None:
                    if end_date_i < end_date_prev:
                        raise ValueError("Spending profiles must be in order")

        # Validate that the last profile has no end_date
        if spending_profiles[-1].end_date:
            raise ValueError("Last spending profile should have no end date")


class Spending(BaseModel):
    """
    Attributes
        spending_strategy (SpendingOptions): Defaults to `inflation_only` strategy

        profiles (list[SpendingProfile])
    """

    spending_strategy: SpendingOptions = Field(
        default_factory=lambda: SpendingOptions(
            inflation_only=StrategyConfig(chosen=True)
        ),
        json_schema_extra={
            "ui": {
                "label": "Spending Strategy",
                "tooltip": "Strategy for adjusting spending over time (inflation_only, etc.)",
                "section": "Spending",
            }
        },
    )
    profiles: list[SpendingProfile] = Field(
        json_schema_extra={
            "ui": {
                "label": "Spending Profiles",
                "tooltip": "List of spending profiles over different time periods",
                "section": "Spending",
            }
        }
    )

    @model_validator(mode="after")
    def validate_profiles(self):
        """Spending profiles must be in order and last profile should have no end date"""
        _spending_profiles_validation(self.profiles)
        return self
