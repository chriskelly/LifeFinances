from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from urllib.request import Request

from simulation.market_data.fetch import (
    FRED_T10YIE_SERIES_ID,
    fred_observations,
    parse_fred_observations,
)


def test_parse_fred_observations_skips_non_numeric_rows() -> None:
    payload = json.dumps(
        {
            "observations": [
                {"date": "2026-01-02", "value": "2.35"},
                {"date": "2026-01-05", "value": "."},
                {"date": "2026-01-06", "value": "2.40"},
            ]
        }
    )

    pairs = parse_fred_observations(payload)

    assert pairs == [
        (date(2026, 1, 2), Decimal("2.35")),
        (date(2026, 1, 6), Decimal("2.40")),
    ]


def test_fred_series_constant_names_t10yie() -> None:
    # Contract test: this is the FRED series tpaw uses for suggested inflation.
    assert FRED_T10YIE_SERIES_ID == "T10YIE"


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body.encode("utf-8")


def test_fred_observations_builds_official_json_api_request() -> None:
    captured: dict[str, object] = {}
    expected_key = "fred-request-key"
    observation_start = date(2026, 1, 1)
    payload = json.dumps({"observations": [{"date": "2026-01-02", "value": "2.35"}]})
    timeout = 7.5

    def opener(request: Request, timeout: float):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return _FakeResponse(payload)

    pairs = fred_observations(
        api_key=expected_key,
        observation_start=observation_start,
        timeout_seconds=timeout,
        opener=opener,
    )

    assert pairs == [(date(2026, 1, 2), Decimal("2.35"))]
    assert "series_id=T10YIE" in str(captured["url"])
    assert f"api_key={expected_key}" in str(captured["url"])
    assert "file_type=json" in str(captured["url"])
    assert f"observation_start={observation_start.isoformat()}" in str(captured["url"])
    assert captured["timeout"] == timeout
