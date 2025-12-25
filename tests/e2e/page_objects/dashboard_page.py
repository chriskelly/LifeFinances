"""Dashboard Page Object Model for E2E tests."""
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from tests.e2e.page_objects.base_page import BasePage


class DashboardPage(BasePage):
    """Page Object for the Dashboard page."""

    # Locators
    NAVIGATION_DASHBOARD = (By.LINK_TEXT, "Dashboard")
    NAVIGATION_CONFIG = (By.LINK_TEXT, "Configuration")
    NAVIGATION_RUN = (By.LINK_TEXT, "Run Simulation")
    NAVIGATION_RESULTS = (By.LINK_TEXT, "Results")

    STAT_CONFIG_COUNT = (By.ID, "stat-config-count")
    STAT_SIMULATIONS_RUN = (By.ID, "stat-simulations-run")
    STAT_SUCCESS_RATE = (By.ID, "stat-success-rate")

    RECENT_SIMULATIONS_SECTION = (By.ID, "recent-simulations")
    RECENT_SIMULATION_CARDS = (By.CSS_SELECTOR, ".simulation-card")

    QUICK_ACTION_CONFIG = (By.ID, "quick-action-config")
    QUICK_ACTION_RUN = (By.ID, "quick-action-run")

    def __init__(self, driver: WebDriver, base_url: str):
        """Initialize Dashboard page."""
        super().__init__(driver, base_url)
        self.path = "/dashboard"

    def navigate(self) -> None:
        """Navigate to dashboard page."""
        self.navigate_to(self.path)

    def click_navigation_config(self) -> None:
        """Click the Configuration navigation link."""
        self.click(*self.NAVIGATION_CONFIG)

    def click_navigation_run(self) -> None:
        """Click the Run Simulation navigation link."""
        self.click(*self.NAVIGATION_RUN)

    def click_navigation_results(self) -> None:
        """Click the Results navigation link."""
        self.click(*self.NAVIGATION_RESULTS)

    def get_config_count(self) -> str:
        """
        Get the configuration count stat.

        Returns:
            Configuration count as string
        """
        return self.get_text(*self.STAT_CONFIG_COUNT)

    def get_simulations_run_count(self) -> str:
        """
        Get the simulations run count stat.

        Returns:
            Simulations run count as string
        """
        return self.get_text(*self.STAT_SIMULATIONS_RUN)

    def get_success_rate(self) -> str:
        """
        Get the success rate stat.

        Returns:
            Success rate as string
        """
        return self.get_text(*self.STAT_SUCCESS_RATE)

    def get_recent_simulation_count(self) -> int:
        """
        Get the number of recent simulations displayed.

        Returns:
            Number of recent simulation cards
        """
        cards = self.find_elements(*self.RECENT_SIMULATION_CARDS)
        return len(cards)

    def click_quick_action_config(self) -> None:
        """Click the quick action button to go to Configuration."""
        self.click(*self.QUICK_ACTION_CONFIG)

    def click_quick_action_run(self) -> None:
        """Click the quick action button to run simulation."""
        self.click(*self.QUICK_ACTION_RUN)

    def is_recent_simulations_visible(self) -> bool:
        """
        Check if recent simulations section is visible.

        Returns:
            True if visible, False otherwise
        """
        return self.is_element_visible(*self.RECENT_SIMULATIONS_SECTION)
