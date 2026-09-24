import sqlite3

from core.models import Plan
from core.repository import PlanRepository, PlanSummary, UnloadablePlan
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


def test_get_by_id_returns_none_for_unloadable_row(
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

    assert repo.get_by_id(plan_id) is None


def test_list_loadable_skips_rows_that_will_not_validate(
    repo: PlanRepository,
) -> None:
    loadable_name = "Good"
    loadable_id, _ = repo.create(name=loadable_name)
    conn = sqlite3.connect(repo.db_path)
    try:
        conn.execute(
            "INSERT INTO plans (name, data) VALUES (?, ?)",
            ("Corrupt", "{not-valid-plan-json"),
        )
        conn.commit()
    finally:
        conn.close()

    loadable = repo.list_loadable()

    assert loadable == [PlanSummary(id=loadable_id, name=loadable_name)]
    assert repo.loadable_ids() == {loadable_id}
