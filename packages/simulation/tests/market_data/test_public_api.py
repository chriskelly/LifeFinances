from __future__ import annotations

from datetime import date

from core.defaults import default_plan

from simulation import build_return_paths, resolve_inflation


def test_public_api_smoke() -> None:
    plan = default_plan()
    months = 12

    paths = build_return_paths(plan, months_per_run=months)
    inflation = resolve_inflation(plan, today=date(2026, 1, 1))

    assert paths.stocks_log.shape == (plan.sampling.num_runs, months)
    assert inflation.source == "suggested"
