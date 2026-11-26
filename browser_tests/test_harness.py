from core.repository import PlanRepository
from playwright.sync_api import Page

from browser_tests.support import LiveApp


def test_app_loads_editor_against_temporary_database(
    editor_page: Page, live_app: LiveApp
) -> None:
    assert editor_page.title() == "LifeFinances"
    assert editor_page.locator("#editor-jobs").count() == 1
    assert editor_page.locator("#results-chart").count() == 1

    # The saved-row test proves a browser write lands in this DB; here we only
    # verify the fixture seeded the plan the app is expected to serve.
    plans = PlanRepository(db_path=live_app.db_path)
    assert plans.loadable_ids() == {1}
