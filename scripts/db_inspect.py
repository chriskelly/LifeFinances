#!/usr/bin/env python3
"""Inspect plans stored in the LifeFinances SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from core.paths import default_db_path


def inspect_plan(plan_id: int) -> None:
    db_path = default_db_path()
    if not db_path.is_file():
        print(
            f"No database at {db_path}. Run: uv run python scripts/init_db.py",
            file=sys.stderr,
        )
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, name, data, created_at, updated_at FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        print(f"Plan {plan_id} not found.", file=sys.stderr)
        sys.exit(1)
    payload = {
        "id": row["id"],
        "name": row["name"],
        "data": json.loads(row["data"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=int, required=True, help="Plan id to print")
    args = parser.parse_args()
    inspect_plan(args.plan)


if __name__ == "__main__":
    main()
