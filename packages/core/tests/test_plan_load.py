import sqlite3

from core.models import Plan
from core.repository import PlanRepository, UnloadablePlan
from pydantic import ValidationError


def test_load_plan_returns_validation_message_for_unloadable_row(
    repo: PlanRepository,
) -> None:
    payload = "{not-valid-plan-json"
    conn = sqlite3.connect(repo.db_path)
    try:
        cur = conn.execute(
            "INSERT INTO plans (name, data) VALUES (?, ?)",
            ("Corrupt", payload),
        )
        conn.commit()
        plan_id = cur.lastrowid
    finally:
        conn.close()
    assert plan_id is not None

    try:
        Plan.model_validate_json(payload)
    except ValidationError as exc:
        expected_message = str(exc)
    else:
        raise AssertionError("payload must fail Plan validation")

    loaded = repo.load_plan(plan_id)

    assert loaded == UnloadablePlan(id=plan_id, message=expected_message)
    assert repo.get_by_id(plan_id) is None
