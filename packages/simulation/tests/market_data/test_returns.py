from __future__ import annotations

from pathlib import Path

import numpy as np
from simulation.market_data.returns import (
    _load_from_csv,
    load_historical_returns,
)

# Pinned contract values copied from tpaw's source of truth
# (v7_raw_monthly_non_log_series.rs / v7_raw_data.csv). These lock the vendored
# CSV to tpaw's data; update only when intentionally bumping the dataset version.
PINNED_START = (1871, 1)
PINNED_LENGTH = 1857
PINNED_FIRST_STOCK_NON_LOG = -0.0117810825569089
PINNED_FIRST_BOND_NON_LOG = -0.025576313862529
PINNED_LAST_STOCK_NON_LOG = 0.0227344987950218
PINNED_LAST_BOND_NON_LOG = 0.00704720957728999


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


def test_default_load_is_memoized() -> None:
    first = load_historical_returns()
    second = load_historical_returns()

    assert first is second


def test_vendored_csv_is_faithful_port_of_tpaw_source() -> None:
    hist = load_historical_returns()

    assert hist.start == PINNED_START
    assert hist.length == PINNED_LENGTH
    # f32-precision tolerance: tpaw bakes the .rs array as f32 literals.
    tol = 1e-7
    assert np.isclose(
        np.expm1(hist.stocks_log[0]), PINNED_FIRST_STOCK_NON_LOG, atol=tol
    )
    assert np.isclose(np.expm1(hist.bonds_log[0]), PINNED_FIRST_BOND_NON_LOG, atol=tol)
    assert np.isclose(
        np.expm1(hist.stocks_log[-1]), PINNED_LAST_STOCK_NON_LOG, atol=tol
    )
    assert np.isclose(np.expm1(hist.bonds_log[-1]), PINNED_LAST_BOND_NON_LOG, atol=tol)


def test_history_is_frozen() -> None:
    hist = load_historical_returns()

    try:
        hist.stocks_log = np.array([0.0])  # type: ignore[misc]
    except AttributeError, TypeError:
        return
    raise AssertionError("HistoricalReturns should be immutable")
