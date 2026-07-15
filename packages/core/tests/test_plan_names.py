from core.plan_names import (
    UNTITLED_PLAN_BASE,
    copy_plan_name,
    next_available_name,
    untitled_plan_name,
)


def test_next_available_name_returns_base_when_unused():
    base = UNTITLED_PLAN_BASE

    assert next_available_name(base=base, existing=[]) == base


def test_next_available_name_suffixes_on_collision():
    base = UNTITLED_PLAN_BASE
    existing = [base, f"{base} 2"]

    assert next_available_name(base=base, existing=existing) == f"{base} 3"


def test_copy_plan_name_uses_copy_suffix_then_numbers():
    original = "My Plan"
    first = copy_plan_name(original_name=original, existing=[original])

    assert first == f"{original} (copy)"

    second = copy_plan_name(
        original_name=original,
        existing=[original, first],
    )

    assert second == f"{original} (copy) 2"


def test_untitled_plan_name_delegates_to_next_available():
    existing = [UNTITLED_PLAN_BASE]

    assert untitled_plan_name(existing=existing) == f"{UNTITLED_PLAN_BASE} 2"
