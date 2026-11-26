from __future__ import annotations

import pytest
from playwright.sync_api import Locator, Page, TimeoutError, expect


def goto_editor(*, page: Page, base_url: str) -> None:
    page.goto(base_url)
    try:
        page.wait_for_function(
            "() => typeof window.htmx !== 'undefined'", timeout=15_000
        )
    except TimeoutError:
        pytest.fail(
            "htmx did not load; the browser checks need network access to "
            "https://unpkg.com/htmx.org."
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
        "element => element.nextElementSibling.classList.contains('row-template')"
    ), "new row must be inserted before the row template"
    return row


def wait_for_existing_index(row: Locator) -> Locator:
    index_input = row.locator(
        ":scope > .row-fields > input[type='hidden'][name$='.existing_index']"
    )
    try:
        expect(index_input).to_have_count(1, timeout=8_000)
    except AssertionError:
        form_error = row.page.locator("#form-error")
        detail = form_error.inner_text() if form_error.is_visible() else "no form error"
        raise AssertionError(
            f"row save did not create existing_index ({detail})"
        ) from None
    return index_input
