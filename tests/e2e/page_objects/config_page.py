"""Configuration Page Object Model for E2E tests."""
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from tests.e2e.page_objects.base_page import BasePage


class ConfigPage(BasePage):
    """Page Object for the Configuration page."""

    # Locators
    CONFIG_TEXTAREA = (By.ID, "config-editor")
    SAVE_BUTTON = (By.ID, "save-config")
    SAVE_AND_RUN_BUTTON = (By.ID, "save-and-run")
    RESET_BUTTON = (By.ID, "reset-config")

    SUCCESS_MESSAGE = (By.CSS_SELECTOR, ".alert-success")
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".alert-danger")

    def __init__(self, driver: WebDriver, base_url: str):
        """Initialize Config page."""
        super().__init__(driver, base_url)
        self.path = "/config"

    def navigate(self) -> None:
        """Navigate to config page."""
        self.navigate_to(self.path)

    def get_config_content(self) -> str:
        """
        Get the current configuration content from the editor.

        Returns:
            Configuration content as string
        """
        return self.get_attribute(*self.CONFIG_TEXTAREA, "value") or ""

    def set_config_content(self, content: str) -> None:
        """
        Set the configuration content in the editor.

        Args:
            content: Configuration YAML content to set
        """
        self.send_keys(*self.CONFIG_TEXTAREA, content)

    def click_save(self) -> None:
        """Click the Save Configuration button."""
        self.click(*self.SAVE_BUTTON)

    def click_save_and_run(self) -> None:
        """Click the Save and Run Simulation button."""
        self.click(*self.SAVE_AND_RUN_BUTTON)

    def click_reset(self) -> None:
        """Click the Reset button."""
        self.click(*self.RESET_BUTTON)

    def is_success_message_visible(self) -> bool:
        """
        Check if success message is visible.

        Returns:
            True if success message is visible, False otherwise
        """
        return self.is_element_visible(*self.SUCCESS_MESSAGE)

    def is_error_message_visible(self) -> bool:
        """
        Check if error message is visible.

        Returns:
            True if error message is visible, False otherwise
        """
        return self.is_element_visible(*self.ERROR_MESSAGE)

    def get_success_message(self) -> str:
        """
        Get the success message text.

        Returns:
            Success message text
        """
        return self.get_text(*self.SUCCESS_MESSAGE)

    def get_error_message(self) -> str:
        """
        Get the error message text.

        Returns:
            Error message text
        """
        return self.get_text(*self.ERROR_MESSAGE)

    def is_config_editor_visible(self) -> bool:
        """
        Check if configuration editor is visible.

        Returns:
            True if editor is visible, False otherwise
        """
        return self.is_element_visible(*self.CONFIG_TEXTAREA)
