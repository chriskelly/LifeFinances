"""Kids configuration classes"""

from pydantic import BaseModel, Field


class Kids(BaseModel):
    """
    Attributes
        cost_of_kid (float)

        birth_years (list[float])
    """

    fraction_of_spending: float = Field(
        json_schema_extra={
            "ui": {
                "label": "Fraction of Spending",
                "tooltip": "Fraction of total spending attributable to each child (e.g., 0.2 = 20%)",
                "section": "Kids",
                "min_value": 0,
                "max_value": 1,
            }
        }
    )
    years_of_support: int = Field(
        json_schema_extra={
            "ui": {
                "label": "Years of Support",
                "tooltip": "Number of years to support each child",
                "section": "Kids",
                "min_value": 0,
                "max_value": 30,
            }
        }
    )
    birth_years: list[float] = Field(
        json_schema_extra={
            "ui": {
                "label": "Birth Years",
                "tooltip": "List of birth years for each child",
                "section": "Kids",
                "widget_type": "list",
            }
        }
    )
