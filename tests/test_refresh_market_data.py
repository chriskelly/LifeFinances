from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core.models import AppSettings  # noqa: E402
from core.settings_repository import SettingsRepository  # noqa: E402

import refresh_market_data  # noqa: E402


def test_refresh_market_data_requires_configured_fred_key(db_path, capsys) -> None:
    exit_code = refresh_market_data.main(["--db-path", str(db_path)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "FRED API key is not configured" in captured.err


def test_refresh_market_data_writes_cache_with_fake_fetcher(
    tmp_path, db_path, capsys
) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key="fred-cli-key"))
    cache_path = tmp_path / "t10yie_daily.csv"
    meta_path = tmp_path / "t10yie_daily.meta.json"

    def fetcher(**kwargs):
        return [(date(2026, 6, 27), Decimal("2.35"))]

    exit_code = refresh_market_data.main(
        [
            "--db-path",
            str(db_path),
            "--cache-path",
            str(cache_path),
            "--meta-path",
            str(meta_path),
        ],
        fetcher=fetcher,
    )

    assert exit_code == 0
    assert "2026-06-27" in cache_path.read_text(encoding="utf-8")
    assert meta_path.is_file()
    captured = capsys.readouterr()
    assert "Wrote T10YIE cache" in captured.out


def test_refresh_market_data_update_vendored_writes_target_path(
    tmp_path, db_path, capsys
) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key="fred-cli-key"))
    vendored_path = tmp_path / "t10yie_daily.csv"

    def fetcher(**kwargs):
        assert kwargs["observation_start"] is None
        return [(date(2026, 6, 27), Decimal("2.35"))]

    exit_code = refresh_market_data.main(
        [
            "--db-path",
            str(db_path),
            "--update-vendored",
            "--vendored-path",
            str(vendored_path),
        ],
        fetcher=fetcher,
    )

    assert exit_code == 0
    assert "2026-06-27" in vendored_path.read_text(encoding="utf-8")
    captured = capsys.readouterr()
    assert "Update PROVENANCE.md" in captured.out


def test_refresh_only_sp500_writes_cache(tmp_path, db_path) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(eod_api_key="eod-cli-key"))
    cache_path = tmp_path / "sp500_close.csv"
    meta_path = tmp_path / "sp500_close.meta.json"
    live_observed = date(2026, 1, 3)
    live_close = Decimal("5200.0")

    def eod_fetcher(**kwargs):
        return [(live_observed, live_close)]

    exit_code = refresh_market_data.main(
        [
            "--db-path",
            str(db_path),
            "--only",
            "sp500",
            "--sp500-cache-path",
            str(cache_path),
            "--sp500-meta-path",
            str(meta_path),
        ],
        eod_fetcher=eod_fetcher,
    )

    assert exit_code == 0
    assert str(live_close) in cache_path.read_text(encoding="utf-8")


def test_refresh_only_treasury_needs_no_key(tmp_path, db_path) -> None:
    from simulation.market_data.cache import TREASURY_TENORS

    SettingsRepository(db_path=db_path).save(AppSettings())  # no keys
    cache_path = tmp_path / "treasury_real_yield.csv"
    meta_path = tmp_path / "treasury_real_yield.meta.json"
    live_observed = date(2026, 1, 3)
    live_yield = Decimal("0.02")

    def treasury_fetcher(**kwargs):
        return [(live_observed, {t: live_yield for t in TREASURY_TENORS})]

    exit_code = refresh_market_data.main(
        [
            "--db-path",
            str(db_path),
            "--only",
            "treasury",
            "--treasury-cache-path",
            str(cache_path),
            "--treasury-meta-path",
            str(meta_path),
        ],
        treasury_fetcher=treasury_fetcher,
    )

    assert exit_code == 0
    assert cache_path.is_file()


def test_refresh_only_treasury_skips_incomplete_rows(tmp_path, db_path) -> None:
    from simulation.market_data.cache import TREASURY_TENORS

    SettingsRepository(db_path=db_path).save(AppSettings())
    cache_path = tmp_path / "treasury_real_yield.csv"
    meta_path = tmp_path / "treasury_real_yield.meta.json"
    complete_observed = date(2026, 1, 3)
    complete_yield = Decimal("0.02")
    incomplete_observed = date(2026, 1, 4)

    def treasury_fetcher(**kwargs):
        return [
            (incomplete_observed, {"20": complete_yield}),
            (complete_observed, {t: complete_yield for t in TREASURY_TENORS}),
        ]

    exit_code = refresh_market_data.main(
        [
            "--db-path",
            str(db_path),
            "--only",
            "treasury",
            "--treasury-cache-path",
            str(cache_path),
            "--treasury-meta-path",
            str(meta_path),
        ],
        treasury_fetcher=treasury_fetcher,
    )

    assert exit_code == 0
    assert complete_observed.isoformat() in cache_path.read_text(encoding="utf-8")
    assert incomplete_observed.isoformat() not in cache_path.read_text(encoding="utf-8")


def test_refresh_only_sp500_without_key_returns_two(db_path, capsys) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings())  # no EOD key

    exit_code = refresh_market_data.main(["--db-path", str(db_path), "--only", "sp500"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "EOD API key is not configured" in captured.err
