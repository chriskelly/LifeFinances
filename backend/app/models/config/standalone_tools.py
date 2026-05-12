"""Standalone tools configuration classes"""

from pydantic import BaseModel, Field, model_validator


class TPAWPlanner(BaseModel):
    """
    Attributes
        group_tol (float): Defaults to 1.0
        inflation_rate (float): Optional constant real annual inflation rate (e.g. 0.02 for 2%).
            When set, the TPAW planner export notebook can override
            the simulated inflation path with a deterministic one based on this rate.
            Defaults to None.
    """

    group_tol: float = Field(
        default=1.0,
        json_schema_extra={
            "ui": {
                "label": "Group Tolerance",
                "tooltip": "Grouping tolerance for TPAW calculations",
                "section": "TPAW",
                "min_value": 0,
                "max_value": 10,
            }
        },
    )
    inflation_rate: float | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Inflation Rate Override",
                "tooltip": "Optional constant inflation rate override (e.g., 0.02 for 2% annual inflation)",
                "section": "TPAW",
                "min_value": 0,
                "max_value": 0.2,
            }
        },
    )


class DisabilityCoverage(BaseModel):
    """
    Attributes
        percentage (float): Defaults to 0.0 (no coverage). When greater than zero, income
            replacement share (e.g. 60.0 for 60% of income).
        duration_years (int | None): Benefit period in calendar years from the start of the
            simulation timeline. Mutually exclusive with age_limit.
        age_limit (int | None): Benefits payable until the insured reaches this age.
            Mutually exclusive with duration_years.

    Rules:
        - Set at most one of duration_years or age_limit.
        - When percentage > 0, set exactly one of them; duration_years must be positive if used.
        - When percentage == 0, leave both unset (None).
    """

    percentage: float = Field(
        default=0.0,
        json_schema_extra={
            "ui": {
                "label": "Coverage Percentage",
                "tooltip": "Percentage of income covered by disability insurance (e.g., 0.6 = 60%)",
                "section": "Insurance",
                "min_value": 0,
                "max_value": 1,
            }
        },
    )
    duration_years: int | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Coverage Duration (years)",
                "tooltip": "Number of years disability insurance coverage lasts",
                "section": "Insurance",
                "min_value": 1,
                "max_value": 40,
            }
        },
    )
    age_limit: int | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Benefit age limit",
                "tooltip": "Disability benefits payable until the insured reaches this age",
                "section": "Insurance",
                "min_value": 18,
                "max_value": 100,
            }
        },
    )

    @model_validator(mode="after")
    def duration_xor_age(self) -> "DisabilityCoverage":
        has_duration = self.duration_years is not None
        has_age = self.age_limit is not None
        if has_duration and has_age:
            msg = "Set only one of duration_years or age_limit, not both."
            raise ValueError(msg)
        if self.percentage > 0:
            if not has_duration and not has_age:
                msg = "When percentage > 0, set either duration_years or age_limit."
                raise ValueError(msg)
            if (
                has_duration
                and self.duration_years is not None
                and self.duration_years <= 0
            ):
                msg = "duration_years must be positive when set."
                raise ValueError(msg)
        elif has_duration or has_age:
            msg = "When percentage is 0, omit both duration_years and age_limit."
            raise ValueError(msg)
        return self


class DisabilityInsuranceCalculator(BaseModel):
    """
    Attributes
        user_disability_coverage (DisabilityCoverage): Defaults to DisabilityCoverage()
        partner_disability_coverage (DisabilityCoverage): Defaults to DisabilityCoverage()
    """

    user_disability_coverage: DisabilityCoverage = Field(
        default_factory=DisabilityCoverage,
        json_schema_extra={
            "ui": {
                "label": "User Disability Coverage",
                "tooltip": "Disability insurance coverage for primary user",
                "section": "Insurance",
            }
        },
    )
    partner_disability_coverage: DisabilityCoverage = Field(
        default_factory=DisabilityCoverage,
        json_schema_extra={
            "ui": {
                "label": "Partner Disability Coverage",
                "tooltip": "Disability insurance coverage for partner/spouse",
                "section": "Insurance",
            }
        },
    )
