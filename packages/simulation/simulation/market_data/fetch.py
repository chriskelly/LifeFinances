from __future__ import annotations

import importlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from types import TracebackType
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_T10YIE_SERIES_ID = "T10YIE"
LOOKBACK_DAYS = 30


class _ReadableResponse(Protocol):
    def read(self) -> bytes: ...


class _ResponseContext(Protocol):
    def __enter__(self) -> _ReadableResponse: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class UrlOpener(Protocol):
    def __call__(self, request: Request, timeout: float) -> _ResponseContext: ...


def _default_opener(request: Request, timeout: float) -> _ResponseContext:
    try:
        truststore = importlib.import_module("truststore")
    except ImportError:
        pass
    else:
        truststore.inject_into_ssl()

    return urlopen(request, timeout=timeout)


def parse_fred_observations(payload: str) -> list[tuple[date, Decimal]]:
    data = json.loads(payload)
    pairs: list[tuple[date, Decimal]] = []

    for row in data.get("observations", []):
        try:
            observation_date = date.fromisoformat(row["date"])
            value = Decimal(row["value"])
        except KeyError, TypeError, ValueError, InvalidOperation:
            continue
        pairs.append((observation_date, value))

    return pairs


def fred_observations(
    *,
    api_key: str,
    observation_start: date | None,
    timeout_seconds: float = 10.0,
    opener: UrlOpener = _default_opener,
) -> list[tuple[date, Decimal]]:
    params = {
        "api_key": api_key,
        "series_id": FRED_T10YIE_SERIES_ID,
        "file_type": "json",
    }
    if observation_start is not None:
        params["observation_start"] = observation_start.isoformat()

    request = Request(f"{FRED_OBSERVATIONS_URL}?{urlencode(params)}")
    with opener(request, timeout_seconds) as response:
        payload = response.read().decode("utf-8")

    return parse_fred_observations(payload)
