"""Spending configuration classes"""

from pydantic import BaseModel, Field, model_validator

from app.models.config.strategy import StrategyConfig, StrategyOptions


class SpendingProfile(BaseModel):
    """Represents a time period with specific yearly spending amount

    Attributes:
        yearly_amount (int): Base yearly spending in thousands
        end_date (float | None): Date when this profile ends (None for final profile)
    """

    yearly_amount: int
    end_date: float | None = None


def _spending_profiles_validation(spending_profiles: list[SpendingProfile]):
    """Validate spending profiles ordering and end_date requirements

    Args:
        spending_profiles: List of spending profiles to validate

    Raises:
        ValueError: If profiles are invalid (empty, out of order, missing/extra end_dates)
    """
    if not spending_profiles:
        raise ValueError("At least one spending profile is required")

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


class InflationFollowingConfig(StrategyConfig):
    """Configuration for inflation-following spending strategy

    This strategy selects spending profiles based on date and applies
    inflation adjustment to the base yearly amount.

    Attributes:
        chosen (bool): Inherited from StrategyConfig - whether this strategy is selected
        profiles (list[SpendingProfile]): Ordered list of spending profiles over time periods
    """

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
        """Validate spending profiles using existing validation logic"""
        _spending_profiles_validation(self.profiles)
        return self


class SpendingStrategyOptions(StrategyOptions):
    """Container for all spending strategy options

    Attributes:
        inflation_following (InflationFollowingConfig): The inflation-following strategy config
    """

    inflation_following: InflationFollowingConfig = Field(
        default_factory=lambda: InflationFollowingConfig(chosen=True, profiles=[]),
        json_schema_extra={
            "ui": {
                "label": "Inflation Following Strategy",
                "tooltip": "Adjust spending based on inflation and spending profiles",
                "section": "Spending",
            }
        },
    )
