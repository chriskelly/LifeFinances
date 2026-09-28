from __future__ import annotations

import re
from pathlib import Path

from simulation.result import PUBLIC_ARRAY_FIELDS
from web.explain import diagnostics_payload, summary_payload

from .explain_fixtures import sample_simulation_result, scoped_result

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
                walk(child_value, f"{prefix}.{child_key}")
            return
        keys.append(prefix)

    for key, value in payload.items():
        if key in {"plan_id", "name"}:
            continue
        walk(value, key)
    return keys


def test_series_names_match_public_array_fields() -> None:
    markdown = OVERVIEW_PATH.read_text(encoding="utf-8")
    assert overview_table_names(markdown=markdown, heading="Series") == list(
        PUBLIC_ARRAY_FIELDS
    )


def test_summary_names_match_flattened_summary_payload() -> None:
    markdown = OVERVIEW_PATH.read_text(encoding="utf-8")
    expected = flatten_payload_keys(
        summary_payload(scoped_result(sample_simulation_result(), plan_name="Overview"))
    )
    assert overview_table_names(markdown=markdown, heading="Summary") == expected


def test_diagnostics_names_match_flattened_diagnostics_payload() -> None:
    markdown = OVERVIEW_PATH.read_text(encoding="utf-8")
    expected = flatten_payload_keys(
        diagnostics_payload(
            scoped_result(sample_simulation_result(), plan_name="Overview")
        )
    )
    assert overview_table_names(markdown=markdown, heading="Diagnostics") == expected
