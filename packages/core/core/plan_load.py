from __future__ import annotations

import json
from datetime import date
from typing import Any

from core.models import Plan


def _calendar_today(today: date) -> dict[str, int | str]:
    return {
        "kind": "calendar_month",
        "year": today.year,
        "month": today.month,
    }


def _coerce_start(item: dict[str, Any], *, today: date) -> None:
    if item.get("start") is None:
        item["start"] = _calendar_today(today)


def coerce_null_starts(data: dict[str, Any], *, today: date) -> dict[str, Any]:
    """Replace null/missing job and manual-stream starts with today's calendar month."""
    household = data.get("household")
    if isinstance(household, dict):
        for person_key in ("person1", "person2"):
            person = household.get(person_key)
            if not isinstance(person, dict):
                continue
            jobs = person.get("jobs")
            if isinstance(jobs, list):
                for job in jobs:
                    if isinstance(job, dict):
                        _coerce_start(job, today=today)
    streams = data.get("manual_income_streams")
    if isinstance(streams, list):
        for stream in streams:
            if isinstance(stream, dict):
                _coerce_start(stream, today=today)
    return data


def parse_plan_json(raw: str | bytes, *, today: date | None = None) -> Plan:
    """Deserialize plan JSON, coercing legacy null job/stream starts."""
    resolved_today = today if today is not None else date.today()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("plan JSON must be an object")
    coerce_null_starts(data, today=resolved_today)
    return Plan.model_validate(data)
