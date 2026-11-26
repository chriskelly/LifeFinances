import pytest
from playwright.sync_api import Page, expect

from browser_tests.support import add_row, open_section, section_rows

ROW_CASES = [
    pytest.param("#editor-jobs", "jobs", "Add job", "Untitled job", id="job"),
    pytest.param(
        "#editor-spending",
        "essential",
        "Add essential spending",
        "Untitled essential spending",
        id="spending",
    ),
    pytest.param(
        "#editor-manual-income",
        "streams",
        "Add income stream",
        "Untitled income stream",
        id="income",
    ),
]


@pytest.mark.parametrize(("section", "prefix", "add_label", "empty_label"), ROW_CASES)
def test_add_row_opens_and_focuses_label(
    editor_page: Page,
    section: str,
    prefix: str,
    add_label: str,
    empty_label: str,
) -> None:
    open_section(page=editor_page, section=section)
    row = add_row(
        section_rows(page=editor_page, section=section, prefix=prefix),
        add_label=add_label,
    )

    expect(
        row.locator(":scope > .row-fields input[data-summary-source]")
    ).to_be_focused()
    expect(row.locator(":scope > summary [data-summary-label]")).to_have_text(
        empty_label
    )


@pytest.mark.parametrize(("section", "prefix", "add_label", "empty_label"), ROW_CASES)
def test_label_typing_updates_summary(
    editor_page: Page,
    section: str,
    prefix: str,
    add_label: str,
    empty_label: str,
) -> None:
    open_section(page=editor_page, section=section)
    row = add_row(
        section_rows(page=editor_page, section=section, prefix=prefix),
        add_label=add_label,
    )
    label = row.locator(":scope > .row-fields input[data-summary-source]")
    summary = row.locator(":scope > summary [data-summary-label]")

    label.fill("  Consulting  ")

    expect(summary).to_have_text("Consulting")


@pytest.mark.parametrize(("section", "prefix", "add_label", "empty_label"), ROW_CASES)
def test_whitespace_label_falls_back_to_empty_label(
    editor_page: Page,
    section: str,
    prefix: str,
    add_label: str,
    empty_label: str,
) -> None:
    open_section(page=editor_page, section=section)
    row = add_row(
        section_rows(page=editor_page, section=section, prefix=prefix),
        add_label=add_label,
    )
    label = row.locator(":scope > .row-fields input[data-summary-source]")
    summary = row.locator(":scope > summary [data-summary-label]")

    label.fill("   ")

    expect(summary).to_have_text(empty_label)
