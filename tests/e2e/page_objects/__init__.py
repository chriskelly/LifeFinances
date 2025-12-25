"""Page Object Model package for E2E tests."""

from tests.e2e.page_objects.base_page import BasePage
from tests.e2e.page_objects.config_page import ConfigPage
from tests.e2e.page_objects.dashboard_page import DashboardPage
from tests.e2e.page_objects.results_page import ResultsPage
from tests.e2e.page_objects.run_page import RunPage

__all__ = [
    "BasePage",
    "ConfigPage",
    "DashboardPage",
    "ResultsPage",
    "RunPage",
]
