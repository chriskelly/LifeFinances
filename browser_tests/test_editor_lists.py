import pytest
from core.repository import PlanRepository
from playwright.sync_api import Page, Response, expect

from browser_tests.support import (
    PLAN_JOBS_PATH,
    SAVE_TIMEOUT_MS,
    LiveApp,
    add_row,
    existing_index_input,
    open_section,
    section_rows,
    wait_for_existing_index,
)

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

    expect(summary).to_have_text(empty_label)
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

    label.fill("Consulting")
    expect(summary).to_have_text("Consulting")

    label.fill("   ")

    expect(summary).to_have_text(empty_label)


def test_sabbatical_add_focuses_start_control(editor_page: Page) -> None:
    open_section(page=editor_page, section="#editor-jobs")
    job = add_row(
        section_rows(page=editor_page, section="#editor-jobs", prefix="jobs"),
        add_label="Add job",
    )
    sabbatical = add_row(
        job.locator(".rows[data-prefix='sabbaticals']"),
        add_label="Add sabbatical",
    )
    start_kind = sabbatical.locator(":scope > .row-fields select.boundary-kind").first

    expect(start_kind).to_be_focused()
    assert (start_kind.get_attribute("name") or "").endswith(".start_kind")


def test_sabbatical_open_state_survives_job_reopen(editor_page: Page) -> None:
    open_section(page=editor_page, section="#editor-jobs")
    job = add_row(
        section_rows(page=editor_page, section="#editor-jobs", prefix="jobs"),
        add_label="Add job",
    )
    sabbatical = add_row(
        job.locator(".rows[data-prefix='sabbaticals']"),
        add_label="Add sabbatical",
    )
    job_summary = job.locator(":scope > summary")

    job_summary.click()
    expect(job).to_have_js_property("open", False)
    assert sabbatical.evaluate("element => element.open") is True

    job_summary.click()
    expect(job).to_have_js_property("open", True)
    assert sabbatical.evaluate("element => element.open") is True

    # Re-adding after the reopen still runs the JS focus and insertion path.
    second = add_row(
        job.locator(".rows[data-prefix='sabbaticals']"),
        add_label="Add sabbatical",
    )
    second_start = second.locator(":scope > .row-fields select.boundary-kind").first
    expect(second_start).to_be_focused()
    assert (second_start.get_attribute("name") or "").endswith(
        ".sabbaticals[1].start_kind"
    )


def test_remove_first_row_focuses_next_summary(editor_page: Page) -> None:
    open_section(page=editor_page, section="#editor-jobs")
    container = section_rows(page=editor_page, section="#editor-jobs", prefix="jobs")
    add_row(container, add_label="Add job")
    add_row(container, add_label="Add job")
    editor_page.on("dialog", lambda dialog: dialog.accept())
    rows = container.locator(":scope > details.row")

    rows.nth(0).get_by_role("button", name="Remove job", exact=True).click()

    expect(rows).to_have_count(1)
    expect(rows.nth(0).locator(":scope > summary")).to_be_focused()


def test_remove_last_row_focuses_previous_then_add_button(
    editor_page: Page,
) -> None:
    open_section(page=editor_page, section="#editor-jobs")
    container = section_rows(page=editor_page, section="#editor-jobs", prefix="jobs")
    add_row(container, add_label="Add job")
    add_row(container, add_label="Add job")
    editor_page.on("dialog", lambda dialog: dialog.accept())
    rows = container.locator(":scope > details.row")

    rows.nth(1).get_by_role("button", name="Remove job", exact=True).click()
    expect(rows).to_have_count(1)
    expect(rows.nth(0).locator(":scope > summary")).to_be_focused()

    rows.nth(0).get_by_role("button", name="Remove job", exact=True).click()
    expect(rows).to_have_count(0)
    expect(container.get_by_role("button", name="Add job", exact=True)).to_be_focused()


def _is_jobs_save(response: Response) -> bool:
    return response.request.method == "PATCH" and PLAN_JOBS_PATH in response.url


def test_removed_rows_stay_removed_after_reload(editor_page: Page) -> None:
    open_section(page=editor_page, section="#editor-jobs")
    container = section_rows(page=editor_page, section="#editor-jobs", prefix="jobs")
    add_row(container, add_label="Add job")
    add_row(container, add_label="Add job")
    editor_page.on("dialog", lambda dialog: dialog.accept())
    rows = container.locator(":scope > details.row")

    with editor_page.expect_response(
        _is_jobs_save, timeout=SAVE_TIMEOUT_MS
    ) as first_save:
        rows.nth(1).get_by_role("button", name="Remove job", exact=True).click()
    assert first_save.value.ok

    with editor_page.expect_response(
        _is_jobs_save, timeout=SAVE_TIMEOUT_MS
    ) as second_save:
        rows.nth(0).get_by_role("button", name="Remove job", exact=True).click()
    assert second_save.value.ok

    editor_page.reload()
    open_section(page=editor_page, section="#editor-jobs")
    expect(
        section_rows(page=editor_page, section="#editor-jobs", prefix="jobs").locator(
            ":scope > details.row"
        )
    ).to_have_count(0)


INDEX_CASES = [
    pytest.param("#editor-jobs", "jobs", "Add job", "Saved job", id="job"),
    pytest.param(
        "#editor-spending",
        "essential",
        "Add essential spending",
        "Saved spending",
        id="spending",
    ),
]


@pytest.mark.parametrize(("section", "prefix", "add_label", "label_text"), INDEX_CASES)
def test_saved_row_keeps_existing_index_inside_row_fields(
    editor_page: Page,
    live_app: LiveApp,
    section: str,
    prefix: str,
    add_label: str,
    label_text: str,
) -> None:
    open_section(page=editor_page, section=section)
    row = add_row(
        section_rows(page=editor_page, section=section, prefix=prefix),
        add_label=add_label,
    )

    row.locator("input[data-summary-source]").fill(label_text)
    index_input = wait_for_existing_index(row)

    expect(index_input).to_have_value("0")
    expect(row.locator(":scope > input")).to_have_count(0)

    # The save is visible in the fixture's temp DB, proving the subprocess used it.
    saved_plan = PlanRepository(db_path=live_app.db_path).get_by_id(1)
    assert saved_plan is not None
    saved_labels = {
        "jobs": [job.label for job in saved_plan.household.person1.jobs],
        "essential": [stream.label for stream in saved_plan.extra_essential_spending],
    }
    assert saved_labels[prefix] == [label_text]

    editor_page.reload()
    open_section(page=editor_page, section=section)
    saved = (
        editor_page.locator(f"{section} details.row").filter(has_text=label_text).first
    )
    expect(existing_index_input(saved)).to_have_value("0")
    expect(saved.locator(":scope > input")).to_have_count(0)
