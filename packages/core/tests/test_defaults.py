from core.defaults import (
    DEFAULT_PERSON1_BIRTH_YEAR,
    DEFAULT_PERSON2_BIRTH_YEAR,
    DEFAULT_PLAN_NAME,
    DEFAULT_SAVINGS_BALANCE,
    default_plan,
)


def test_default_plan_wires_module_constants() -> None:
    plan = default_plan()

    assert plan.name == DEFAULT_PLAN_NAME
    assert plan.household.person1.birth_year == DEFAULT_PERSON1_BIRTH_YEAR
    assert plan.household.person2.birth_year == DEFAULT_PERSON2_BIRTH_YEAR
    assert plan.portfolio.current_savings_balance == DEFAULT_SAVINGS_BALANCE
