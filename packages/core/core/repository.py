from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from core.defaults import default_plan
from core.models import Plan
from core.paths import default_db_path


@dataclass
class PlanRepository:
    db_path: Path

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_by_id(self, plan_id: int) -> Plan | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT data FROM plans WHERE id = ?", (plan_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        try:
            return Plan.model_validate_json(row[0])
        except ValidationError:
            return None

    def save(self, plan_id: int, plan: Plan) -> None:
        payload = plan.model_dump_json()
        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE plans
                SET name = ?, data = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (plan.name, payload, plan_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_or_create_default(self) -> tuple[int, Plan]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, data FROM plans ORDER BY id LIMIT 1"
            ).fetchone()
            if row is not None:
                plan = Plan.model_validate_json(row[1])
                return row[0], plan
            plan = default_plan()
            payload = plan.model_dump_json()
            cur = conn.execute(
                """
                INSERT INTO plans (name, data)
                VALUES (?, ?)
                """,
                (plan.name, payload),
            )
            conn.commit()
            plan_id = cur.lastrowid
            if plan_id is None:
                raise RuntimeError("INSERT into plans did not return a row id")
            return plan_id, plan
        finally:
            conn.close()
