from __future__ import annotations

UNTITLED_PLAN_BASE = "Untitled Plan"


def next_available_name(*, base: str, existing: list[str]) -> str:
    taken = set(existing)
    if base not in taken:
        return base
    n = 2
    while f"{base} {n}" in taken:
        n += 1
    return f"{base} {n}"


def untitled_plan_name(*, existing: list[str]) -> str:
    return next_available_name(base=UNTITLED_PLAN_BASE, existing=existing)


def copy_plan_name(*, original_name: str, existing: list[str]) -> str:
    return next_available_name(base=f"{original_name} (copy)", existing=existing)
