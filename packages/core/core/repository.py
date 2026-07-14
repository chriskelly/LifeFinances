from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from core.defaults import DEFAULT_PLAN_NAME, default_plan
from core.models import Plan
from core.paths import default_db_path
from core.settings_repository import SettingsRepository


@dataclass(frozen=True)
class PlanSummary:
    id: int
    name: str


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

    def list(self) -> list[PlanSummary]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT id, name FROM plans ORDER BY id").fetchall()
        finally:
            conn.close()
        return [PlanSummary(id=row[0], name=row[1]) for row in rows]

    def create(self, *, name: str) -> tuple[int, Plan]:
        plan = default_plan().model_copy(update={"name": name})
        payload = plan.model_dump_json()
        conn = self._connect()
        try:
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

    def ensure_bootstrap(
        self, *, settings_repo: SettingsRepository
    ) -> tuple[int, Plan]:
        summaries = self.list()
        if not summaries:
            plan_id, plan = self.create(name=DEFAULT_PLAN_NAME)
            settings = settings_repo.get()
            settings.default_plan_id = plan_id
            settings_repo.save(settings)
            return plan_id, plan

        settings = settings_repo.get()
        default_plan_id = settings.default_plan_id
        valid_ids = {summary.id for summary in summaries}
        if default_plan_id is None or default_plan_id not in valid_ids:
            default_plan_id = summaries[0].id
            settings.default_plan_id = default_plan_id
            settings_repo.save(settings)

        plan = self.get_by_id(default_plan_id)
        if plan is None:
            raise RuntimeError(f"Default plan {default_plan_id} could not be loaded")
        return default_plan_id, plan

    def get_or_create_default(self) -> tuple[int, Plan]:
        return self.ensure_bootstrap(settings_repo=SettingsRepository(self.db_path))
