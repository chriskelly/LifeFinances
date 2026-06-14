from datetime import date

from core.defaults import default_plan
from core.timeline import horizon_months, person_end_date


def test_horizon_months_uses_later_person_end_date() -> None:
    fixed_today = date(2026, 6, 13)
    plan = default_plan()
    person1 = plan.household.person1
    person2 = plan.household.person2
    later_end_offset_years = 5
    person2.birth_year = person1.birth_year + later_end_offset_years

    result = horizon_months(plan, today=fixed_today)

    person1_end = person_end_date(person1)
    person2_end = person_end_date(person2)
    later_end = max(person1_end, person2_end)
    expected = (later_end.year - fixed_today.year) * 12 + (
        later_end.month - fixed_today.month
    )

    assert person2_end == later_end
    assert result == expected
