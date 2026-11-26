from playwright.sync_api import Page, expect

PLOTLY_STUB = """
() => {
  window.__plotlyResizeTargets = [];
  window.Plotly = {
    Plots: {
      resize: function (element) {
        window.__plotlyResizeTargets.push(element.id);
      },
    },
  };
  document.getElementById("results-chart").classList.add("js-plotly-plot");
}
"""


def test_pane_toggle_updates_class_aria_and_storage(editor_page: Page) -> None:
    root = editor_page.locator("html")
    button = editor_page.locator("#toggle-editor")

    expect(button).to_have_attribute("aria-expanded", "true")
    button.click()
    assert root.evaluate("element => element.classList.contains('editor-hidden')")
    expect(button).to_have_attribute("aria-expanded", "false")
    assert editor_page.evaluate(
        "JSON.parse(localStorage.getItem('lifeFinances.panes'))"
    ) == {"editorHidden": True}

    button.click()
    assert not root.evaluate("element => element.classList.contains('editor-hidden')")
    expect(button).to_have_attribute("aria-expanded", "true")


def test_pane_toggle_resizes_chart(editor_page: Page) -> None:
    expect(editor_page.locator("#results-chart")).to_have_count(1)
    editor_page.evaluate(PLOTLY_STUB)
    button = editor_page.locator("#toggle-editor")

    button.click()
    editor_page.wait_for_function("window.__plotlyResizeTargets.length === 1")
    assert editor_page.evaluate("window.__plotlyResizeTargets[0]") == "results-chart"

    button.click()
    editor_page.wait_for_function("window.__plotlyResizeTargets.length === 2")


def test_corrupt_panes_storage_falls_back_to_visible(editor_page: Page) -> None:
    root = editor_page.locator("html")
    button = editor_page.locator("#toggle-editor")
    editor_page.evaluate(
        "localStorage.setItem('lifeFinances.panes', '{\"editorHidden\": true}')"
    )
    editor_page.reload()
    assert root.evaluate("element => element.classList.contains('editor-hidden')")

    errors: list[str] = []
    editor_page.on("pageerror", lambda error: errors.append(str(error)))
    editor_page.evaluate("localStorage.setItem('lifeFinances.panes', '{not json')")
    editor_page.reload()

    assert not root.evaluate("element => element.classList.contains('editor-hidden')")
    expect(button).to_have_attribute("aria-expanded", "true")
    assert errors == []

    button.click()
    assert root.evaluate("element => element.classList.contains('editor-hidden')")
    assert editor_page.evaluate(
        "JSON.parse(localStorage.getItem('lifeFinances.panes'))"
    ) == {"editorHidden": True}
