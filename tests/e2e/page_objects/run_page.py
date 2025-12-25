"""Run Simulation Page Object Model for E2E tests."""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from tests.e2e.page_objects.base_page import BasePage


class RunPage(BasePage):
    """Page Object for the Run Simulation page."""

    # Locators
    RUN_BUTTON = (By.ID, "run-simulation")
    CANCEL_BUTTON = (By.ID, "cancel-simulation")

    CONFIG_PREVIEW = (By.ID, "config-preview")
    PROGRESS_BAR = (By.CSS_SELECTOR, ".progress-bar")
    PROGRESS_TEXT = (By.ID, "progress-text")

    SPINNER = (By.CSS_SELECTOR, ".spinner-border")
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".alert-danger")

    def __init__(self, driver: WebDriver, base_url: str):
        """Initialize Run page."""
        super().__init__(driver, base_url)
        self.path = "/run"

    def navigate(self) -> None:
        """Navigate to run page."""
        self.navigate_to(self.path)

    def click_run_simulation(self) -> None:
        """Click the Run Simulation button."""
        self.click(*self.RUN_BUTTON)

    def click_cancel(self) -> None:
        """Click the Cancel button."""
        self.click(*self.CANCEL_BUTTON)

    def is_run_button_enabled(self) -> bool:
        """
        Check if run button is enabled.

        Returns:
            True if run button is enabled, False otherwise
        """
        element = self.find_element(*self.RUN_BUTTON)
        return element.is_enabled()

    def is_config_preview_visible(self) -> bool:
        """
        Check if configuration preview is visible.

        Returns:
            True if visible, False otherwise
        """
        return self.is_element_visible(*self.CONFIG_PREVIEW)

    def get_config_preview(self) -> str:
        """
        Get the configuration preview content.

        Returns:
            Configuration preview text
        """
        return self.get_text(*self.CONFIG_PREVIEW)

    def is_progress_bar_visible(self) -> bool:
        """
        Check if progress bar is visible during simulation.

        Returns:
            True if progress bar is visible, False otherwise
        """
        return self.is_element_visible(*self.PROGRESS_BAR)

    def get_progress_text(self) -> str:
        """
        Get the progress text during simulation.

        Returns:
            Progress text
        """
        return self.get_text(*self.PROGRESS_TEXT)

    def is_spinner_visible(self) -> bool:
        """
        Check if loading spinner is visible.

        Returns:
            True if spinner is visible, False otherwise
        """
        return self.is_element_visible(*self.SPINNER, timeout=1)

    def wait_for_simulation_complete(self, timeout: int = 60) -> bool:
        """
        Wait for simulation to complete (spinner disappears).

        Args:
            timeout: Maximum time to wait in seconds (default 60)

        Returns:
            True if simulation completed, False if timeout
        """
        return self.wait_for_element_to_disappear(*self.SPINNER, timeout=timeout)

    def is_error_message_visible(self) -> bool:
        """
        Check if error message is visible.

        Returns:
            True if error message is visible, False otherwise
        """
        return self.is_element_visible(*self.ERROR_MESSAGE)

    def get_error_message(self) -> str:
        """
        Get the error message text.

        Returns:
            Error message text
        """
        return self.get_text(*self.ERROR_MESSAGE)
