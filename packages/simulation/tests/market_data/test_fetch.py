from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal
from urllib.request import Request

import pytest
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


def test_fred_observations_logs_fetch_failure(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)

    def opener(request: Request, timeout: float):
        raise RuntimeError("network unavailable")

    with pytest.raises(RuntimeError, match="network unavailable"):
        fred_observations(
            api_key="fred-request-key",
            observation_start=date(2026, 1, 1),
            opener=opener,
        )

    assert "FRED T10YIE fetch failed" in caplog.text


def test_parse_fred_observations_logs_api_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    payload = json.dumps({"error_code": 400, "error_message": "Bad Request"})

    pairs = parse_fred_observations(payload)

    assert pairs == []
    assert "FRED API returned an error" in caplog.text


def test_parse_eod_close_reads_close_and_skips_bad_rows() -> None:
    from simulation.market_data.fetch import parse_eod_close

    good_date = date(2026, 1, 2)
    good_close = Decimal("4700.10")
    skipped_date = date(2026, 1, 5)
    second_good_date = date(2026, 1, 6)
    second_good_close = Decimal("4725.50")
    payload = json.dumps(
        [
            {
                "date": good_date.isoformat(),
                "close": float(good_close),
                "adjusted_close": float(good_close),
            },
            {
                "date": skipped_date.isoformat(),
                "close": "bad",
                "adjusted_close": 4725.50,
            },
            {
                "date": second_good_date.isoformat(),
                "close": float(second_good_close),
                "adjusted_close": float(second_good_close),
            },
        ]
    )

    pairs = parse_eod_close(payload)

    assert pairs == [
        (good_date, good_close),
        (second_good_date, second_good_close),
    ]


def test_eod_gspc_close_builds_request() -> None:
    from simulation.market_data.fetch import EOD_SP500_SYMBOL, eod_gspc_close

    captured: dict[str, object] = {}
    expected_key = "eod-request-key"
    from_date = date(2026, 1, 1)
    observed = date(2026, 1, 2)
    expected_close = Decimal("4700.10")
    payload = json.dumps(
        [
            {
                "date": observed.isoformat(),
                "close": float(expected_close),
                "adjusted_close": float(expected_close),
            }
        ]
    )

    def opener(request: Request, timeout: float):
        captured["url"] = request.full_url
        return _FakeResponse(payload)

    pairs = eod_gspc_close(api_key=expected_key, from_date=from_date, opener=opener)

    assert pairs == [(observed, expected_close)]
    assert EOD_SP500_SYMBOL in str(captured["url"])
    assert f"api_token={expected_key}" in str(captured["url"])
    assert "fmt=json" in str(captured["url"])
    assert f"from={from_date.isoformat()}" in str(captured["url"])
