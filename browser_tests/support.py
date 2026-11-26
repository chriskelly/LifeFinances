from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from playwright.sync_api import Locator, Page, TimeoutError, expect

SAVE_TIMEOUT_MS = 8_000
# Mirrors web.routes.PLAN_JOBS; importing web here would build an app bound to
# the developer's real database in the pytest process.
PLAN_JOBS_PATH = "/plan/jobs"
EXISTING_INDEX_SUFFIX = ".existing_index"


@dataclass(frozen=True)
class LiveApp:
    base_url: str
    db_path: Path


def goto_editor(*, page: Page, base_url: str) -> None:
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_function(
            "() => typeof window.htmx !== 'undefined'", timeout=15_000
        )
    except TimeoutError:
        pytest.fail(
            "The editor page did not finish loading. htmx comes from "
            "https://unpkg.com/htmx.org; check network access to that CDN."
        )


def open_section(*, page: Page, section: str) -> None:
    details = page.locator(section)
    if not details.evaluate("element => element.open"):
        details.locator(":scope > summary").click()


def section_rows(*, page: Page, section: str, prefix: str) -> Locator:
    return page.locator(f"{section} .rows[data-prefix='{prefix}']").first


def add_row(container: Locator, *, add_label: str) -> Locator:
    index = container.locator(":scope > details.row").count()
    container.get_by_role("button", name=add_label, exact=True).click()
    row = container.locator(":scope > details.row").nth(index)
    expect(row).to_have_js_property("open", True)
    assert row.evaluate(
        "element => Boolean(element.nextElementSibling && "
        "element.nextElementSibling.classList.contains('row-template'))"
    ), "new row must be inserted before the row template"
    return row


def existing_index_input(row: Locator) -> Locator:
    return row.locator(
        f":scope > .row-fields > input[type='hidden'][name$='{EXISTING_INDEX_SUFFIX}']"
    )


def wait_for_existing_index(row: Locator) -> Locator:
    index_input = existing_index_input(row)
    try:
        expect(index_input).to_have_count(1, timeout=SAVE_TIMEOUT_MS)
    except AssertionError:
        form_error = row.page.locator("#form-error")
        detail = form_error.inner_text() if form_error.is_visible() else "no form error"
        raise AssertionError(
            f"row save did not create existing_index ({detail})"
        ) from None
    return index_input
