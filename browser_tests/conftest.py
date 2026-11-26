from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from core.db_bootstrap import materialize_blank_db
from core.models import InflationConfig
from core.paths import default_db_path, repo_root
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from browser_tests.support import goto_editor


@dataclass(frozen=True)
class LiveApp:
    base_url: str
    db_path: Path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(
    *,
    base_url: str,
    process: subprocess.Popen[bytes],
    log_path: Path,
    timeout: float = 20.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(
                "uvicorn exited before serving requests:\n"
                f"{log_path.read_text(encoding='utf-8')[-4_000:]}"
            )
        try:
            with urllib.request.urlopen(f"{base_url}/favicon.ico", timeout=0.5):
                return
        except urllib.error.URLError, TimeoutError, ConnectionError:
            time.sleep(0.05)
    pytest.fail(f"uvicorn did not answer on {base_url} within {timeout:.0f}s")


def _seed_offline_plan(db_path: Path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, plan = plans.ensure_bootstrap(settings_repo=settings)
    # The browser harness never needs market data: manual inflation and fixed
    # returns keep the first page load offline and deterministic.
    plan.inflation = InflationConfig(mode="manual", manual_annual_rate=Decimal("0.025"))
    plan.planning_returns.preset = "fixed"
    plans.save(plan_id, plan)


@pytest.fixture(scope="session")
def playwright_instance() -> Iterator[Playwright]:
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Iterator[Browser]:
    try:
        browser = playwright_instance.chromium.launch(headless=True)
    except PlaywrightError as exc:
        pytest.fail(
            "Chromium is not installed. Run `make browser-checks` to install it; "
            "on Linux use `uv run playwright install --with-deps chromium`.\n"
            f"{exc}"
        )
        raise
    yield browser
    browser.close()


@pytest.fixture
def live_app(tmp_path: Path) -> Iterator[LiveApp]:
    db_path = materialize_blank_db(tmp_path / "browser.db")
    assert db_path.resolve() != default_db_path().resolve()
    _seed_offline_plan(db_path)
    port = _free_port()
    log_path = tmp_path / "uvicorn.log"
    env = {**os.environ, "LIFE_FINANCES_DB_PATH": str(db_path)}
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "web.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            cwd=repo_root(),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        live = LiveApp(base_url=f"http://127.0.0.1:{port}", db_path=db_path)
        try:
            _wait_for_server(base_url=live.base_url, process=process, log_path=log_path)
            yield live
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    context = browser.new_context()
    # Neither CDN affects editor JS behavior; blocking them keeps runs offline.
    context.route("https://cdn.plot.ly/**", lambda route: route.abort())
    context.route("https://cdn.jsdelivr.net/**", lambda route: route.abort())
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def editor_page(page: Page, live_app: LiveApp) -> Page:
    goto_editor(page=page, base_url=live_app.base_url)
    return page
