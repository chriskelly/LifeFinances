from core.repository import PlanRepository
from playwright.sync_api import Page

from browser_tests.conftest import LiveApp


def test_app_loads_editor_against_temporary_database(
    editor_page: Page, live_app: LiveApp
) -> None:
    assert editor_page.title() == "LifeFinances"
    assert editor_page.locator("#editor-jobs").count() == 1
    assert editor_page.locator("#results-chart").count() == 1

    plans = PlanRepository(db_path=live_app.db_path)
    assert plans.loadable_ids() == {1}
