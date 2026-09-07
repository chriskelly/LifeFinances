from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest
from simulation.market_data.presets_data import load_cape_regression
from simulation.market_data.returns import (
    V8_EFFECTIVE_DATE,
    _load_from_csv,
    load_historical_returns,
)

# Pinned contract values from tpaw v8_raw_data.csv (vendored verbatim).
# Update only when intentionally bumping the historical-returns dataset version.
PINNED_START = (1871, 1)
PINNED_LENGTH = 1863
PINNED_FIRST_STOCK_NON_LOG = -0.011781082556909
PINNED_FIRST_BOND_NON_LOG = -0.025576313862529
PINNED_LAST_STOCK_NON_LOG = 0.0376602969072095
PINNED_LAST_BOND_NON_LOG = -0.010507630080915


def _write_csv(path: Path, rows: list[str]) -> Path:
    header = "year,month,CAPE,stock real return,bond real return"
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def test_log_conversion_round_trips_to_source_non_log_values(tmp_path: Path) -> None:
    stock_non_log = 0.05
    bond_non_log = -0.02
    csv = _write_csv(
        tmp_path / "tiny.csv", [f"2000,1,NA,{stock_non_log},{bond_non_log}"]
    )

    hist = _load_from_csv(csv)

    assert np.isclose(np.expm1(hist.stocks_log[0]), stock_non_log)
    assert np.isclose(np.expm1(hist.bonds_log[0]), bond_non_log)


def test_load_reports_length_and_start(tmp_path: Path) -> None:
    rows = ["2000,1,NA,0.01,0.01", "2000,2,NA,0.02,0.02"]
    csv = _write_csv(tmp_path / "two.csv", rows)

    hist = _load_from_csv(csv)

    assert hist.length == len(rows)
    assert hist.start == (2000, 1)


def test_load_honors_explicit_effective_date(tmp_path: Path) -> None:
    effective = date(2030, 1, 15)
    csv = _write_csv(tmp_path / "one.csv", ["2000,1,NA,0.01,0.01"])

    hist = _load_from_csv(csv, effective_date=effective)

    assert hist.effective_date == effective


def test_load_rejects_empty_returns_csv(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "empty.csv", [])

    with pytest.raises(ValueError, match="no monthly returns rows"):
        _load_from_csv(csv)


def test_default_load_is_memoized() -> None:
    first = load_historical_returns()
    second = load_historical_returns()

    assert first is second


def test_vendored_csv_is_faithful_port_of_tpaw_source() -> None:
    hist = load_historical_returns()

    assert hist.start == PINNED_START
    assert hist.length == PINNED_LENGTH
    assert hist.effective_date == V8_EFFECTIVE_DATE
    assert np.expm1(hist.stocks_log[0]) == PINNED_FIRST_STOCK_NON_LOG
    assert np.expm1(hist.bonds_log[0]) == PINNED_FIRST_BOND_NON_LOG
    assert np.expm1(hist.stocks_log[-1]) == PINNED_LAST_STOCK_NON_LOG
    assert np.expm1(hist.bonds_log[-1]) == PINNED_LAST_BOND_NON_LOG


def test_returns_effective_date_matches_cape_regression_bundle() -> None:
    assert V8_EFFECTIVE_DATE == load_cape_regression().effective_date


def test_history_is_frozen() -> None:
    hist = load_historical_returns()

    try:
        hist.stocks_log = np.array([0.0])  # type: ignore[misc]
    except AttributeError, TypeError:
        return
    raise AssertionError("HistoricalReturns should be immutable")
