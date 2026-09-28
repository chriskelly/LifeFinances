from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
from core.defaults import default_plan
from simulation.diagnostics import empty_diagnostics
from simulation.result import PUBLIC_ARRAY_FIELDS, ResolvedAssumptions, SimulationResult
from web.explain import ScopedResult, diagnostics_payload, summary_payload

OVERVIEW_PATH = Path(__file__).resolve().parents[1] / "OVERVIEW.md"
_HEADING_RE = re.compile(r"^## (.+)$", re.M)
_NAME_CELL_RE = re.compile(r"^\| `([^`]+)` \|", re.M)


def overview_table_names(*, markdown: str, heading: str) -> list[str]:
    matches = list(_HEADING_RE.finditer(markdown))
    for index, match in enumerate(matches):
        if match.group(1) != heading:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        return _NAME_CELL_RE.findall(markdown[start:end])
    raise AssertionError(f"missing ## {heading} in overview")


def flatten_payload_keys(payload: dict[str, object]) -> list[str]:
    keys: list[str] = []

    def walk(value: object, prefix: str) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                child_prefix = f"{prefix}.{child_key}" if prefix else child_key
                walk(child_value, child_prefix)
            return
        keys.append(prefix)

    for key, value in payload.items():
        if key in {"plan_id", "name"}:
            continue
        walk(value, key)
    return keys


def _scoped_result() -> ScopedResult:
    percentiles = [10, 50, 90]
    months = 4
    percentile_values = np.arange(
        1.0, 1.0 + len(percentiles) * months, dtype=np.float64
    ).reshape(len(percentiles), months)
    horizon_values = np.arange(101.0, 101.0 + months, dtype=np.float64)
    result = SimulationResult(
        ran_at=datetime(2026, 9, 23, 8, 30),
        horizon_months=months,
        num_runs=250,
        percentiles=percentiles,
        start_month=(2026, 9),
        balance_start=percentile_values.copy(),
        withdrawals_essential=percentile_values.copy(),
        withdrawals_discretionary=percentile_values.copy(),
        withdrawals_general=percentile_values.copy(),
        withdrawals_total=percentile_values.copy(),
        savings_stock_allocation=percentile_values.copy(),
        wealth_job=horizon_values,
        wealth_social_security=horizon_values + 10.0,
        wealth_pension=horizon_values + 20.0,
        wealth_manual=horizon_values + 30.0,
        num_runs_insufficient=7,
        diagnostics=empty_diagnostics(months=months),
        resolved_assumptions=ResolvedAssumptions(
            annual_inflation=0.02,
            annual_stock_return=0.05,
            annual_bond_return=0.03,
            annual_stock_log_variance=0.04,
            planning_preset="fixed",
            inflation_source="manual",
        ),
    )
    plan = default_plan().model_copy(update={"name": "Overview"})
    return ScopedResult(plan_id=1, plan=plan, result=result)


def test_series_names_match_public_array_fields() -> None:
    markdown = OVERVIEW_PATH.read_text(encoding="utf-8")
    assert overview_table_names(markdown=markdown, heading="Series") == list(
        PUBLIC_ARRAY_FIELDS
    )


def test_summary_names_match_flattened_summary_payload() -> None:
    markdown = OVERVIEW_PATH.read_text(encoding="utf-8")
    expected = flatten_payload_keys(summary_payload(_scoped_result()))
    assert overview_table_names(markdown=markdown, heading="Summary") == expected


def test_diagnostics_names_match_flattened_diagnostics_payload() -> None:
    markdown = OVERVIEW_PATH.read_text(encoding="utf-8")
    expected = flatten_payload_keys(diagnostics_payload(_scoped_result()))
    assert overview_table_names(markdown=markdown, heading="Diagnostics") == expected
