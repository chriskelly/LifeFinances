"""Standalone tools configuration classes"""

from pydantic import BaseModel, Field


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
        percentage (float): Defaults to 0.0
        duration_years (int): Defaults to 0
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
    duration_years: int = Field(
        default=0,
        json_schema_extra={
            "ui": {
                "label": "Coverage Duration (years)",
                "tooltip": "Number of years disability insurance coverage lasts",
                "section": "Insurance",
                "min_value": 0,
                "max_value": 40,
            }
        },
    )


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
