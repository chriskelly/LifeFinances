from __future__ import annotations

import csv
import importlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from types import TracebackType
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_T10YIE_SERIES_ID = "T10YIE"
LOOKBACK_DAYS = 30

logger = logging.getLogger(__name__)


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
    # Python's urllib uses its bundled cert bundle. On macOS that often fails HTTPS
    # verification against public APIs (including FRED) because the interpreter does
    # not automatically trust the OS keychain the way Safari does.
    #
    # truststore patches ssl to use the platform trust store when available. We import
    # lazily and tolerate ImportError so simulation stays usable without this optional
    # dev dependency — callers fall back to vendored data if the fetch fails.
    try:
        truststore = importlib.import_module("truststore")
    except ImportError:
        pass
    else:
        truststore.inject_into_ssl()

    return urlopen(request, timeout=timeout)


def parse_fred_observations(payload: str) -> list[tuple[date, Decimal]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.exception("FRED T10YIE response was not valid JSON")
        raise

    if "error_message" in data or "error_code" in data:
        logger.warning(
            "FRED API returned an error for %s: %s",
            FRED_T10YIE_SERIES_ID,
            data.get("error_message", data.get("error_code")),
        )
        return []

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
    try:
        with opener(request, timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        pairs = parse_fred_observations(payload)
    except Exception:
        logger.exception(
            "FRED T10YIE fetch failed for series %s",
            FRED_T10YIE_SERIES_ID,
        )
        raise

    if not pairs:
        logger.warning(
            "FRED T10YIE fetch returned no usable observations for series %s",
            FRED_T10YIE_SERIES_ID,
        )

    return pairs


EOD_BASE_URL = "https://eodhistoricaldata.com/api/eod"
EOD_SP500_SYMBOL = "GSPC.INDX"


def parse_eod_close(payload: str) -> list[tuple[date, Decimal]]:
    try:
        rows = json.loads(payload)
    except json.JSONDecodeError:
        logger.exception("EOD %s response was not valid JSON", EOD_SP500_SYMBOL)
        raise

    if not isinstance(rows, list):
        logger.warning("EOD %s response was not a JSON array", EOD_SP500_SYMBOL)
        return []

    pairs: list[tuple[date, Decimal]] = []
    for row in rows:
        try:
            observed = date.fromisoformat(row["date"])
            close = Decimal(str(row["close"]))
        except KeyError, TypeError, ValueError, InvalidOperation:
            continue
        pairs.append((observed, close))
    return pairs


def eod_gspc_close(
    *,
    api_key: str,
    from_date: date,
    timeout_seconds: float = 10.0,
    opener: UrlOpener = _default_opener,
) -> list[tuple[date, Decimal]]:
    params = {
        "api_token": api_key,
        "fmt": "json",
        "period": "d",
        "order": "a",
        "from": from_date.isoformat(),
    }
    request = Request(
        f"{EOD_BASE_URL}/{EOD_SP500_SYMBOL}?{urlencode(params)}",
        headers={"Cache-Control": "no-cache"},
    )
    try:
        with opener(request, timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        pairs = parse_eod_close(payload)
    except Exception:
        logger.exception("EOD %s fetch failed", EOD_SP500_SYMBOL)
        raise

    if not pairs:
        logger.warning("EOD %s fetch returned no usable rows", EOD_SP500_SYMBOL)
    return pairs


TREASURY_REAL_YIELD_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/daily-treasury-rates.csv"
)
TREASURY_REAL_YIELD_TYPE = "daily_treasury_real_yield_curve"
# Treasury CSV column label -> tenor key we expose.
_TREASURY_COLUMNS = {
    "5 YR": "5",
    "7 YR": "7",
    "10 YR": "10",
    "20 YR": "20",
    "30 YR": "30",
}


def parse_treasury_real_yields(csv_text: str) -> list[tuple[date, dict[str, Decimal]]]:
    reader = csv.reader(csv_text.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return []

    tenor_by_index = {
        index: _TREASURY_COLUMNS[label]
        for index, label in enumerate(header)
        if label in _TREASURY_COLUMNS
    }

    rows: list[tuple[date, dict[str, Decimal]]] = []
    for cols in reader:
        if not cols:
            continue
        try:
            observed = datetime.strptime(cols[0], "%m/%d/%Y").date()
        except ValueError:
            continue
        yields: dict[str, Decimal] = {}
        for index, tenor in tenor_by_index.items():
            if index >= len(cols):
                continue
            try:
                yields[tenor] = Decimal(cols[index]) / Decimal(100)
            except InvalidOperation:
                continue
        if yields:
            rows.append((observed, yields))
    return rows


def treasury_real_yield_curve(
    *,
    year: int,
    timeout_seconds: float = 10.0,
    opener: UrlOpener = _default_opener,
) -> list[tuple[date, dict[str, Decimal]]]:
    params = {"type": TREASURY_REAL_YIELD_TYPE, "field_tdr_date_value": str(year)}
    request = Request(
        f"{TREASURY_REAL_YIELD_URL}/{year}/all?{urlencode(params)}",
        headers={"Cache-Control": "no-cache"},
    )
    try:
        with opener(request, timeout_seconds) as response:
            csv_text = response.read().decode("utf-8")
        rows = parse_treasury_real_yields(csv_text)
    except Exception:
        logger.exception("Treasury real-yield fetch failed for %s", year)
        raise

    if not rows:
        logger.warning("Treasury real-yield fetch returned no usable rows for %s", year)
    return rows
