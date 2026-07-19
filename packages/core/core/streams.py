from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

PersonId = Literal["person1", "person2"]


class CalendarMonthBoundary(BaseModel):
    kind: Literal["calendar_month"] = "calendar_month"
    year: int
    month: int = Field(ge=1, le=12)


class PersonAgeBoundary(BaseModel):
    kind: Literal["person_age"] = "person_age"
    person: PersonId
    age_months: int = Field(ge=0)


class PersonMaxAgeBoundary(BaseModel):
    kind: Literal["person_max_age"] = "person_max_age"
    person: PersonId


Boundary = Annotated[
    CalendarMonthBoundary | PersonAgeBoundary | PersonMaxAgeBoundary,
    Field(discriminator="kind"),
]


class TimedStream(BaseModel):
    """A monthly recurring income or spending stream over a bounded window.

    Amounts are face amounts in the stream's OWN basis. Inflation is never
    applied here (see spec section 6); `is_nominal` is carried metadata for the
    simulation layer.
    """

    label: str | None = None
    monthly_amount: Decimal = Field(ge=0)
    start: Boundary | None = None
    end: Boundary | None = None
    is_nominal: bool = False
    annual_growth_rate: Decimal = Decimal(0)
