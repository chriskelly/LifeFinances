"""
Base Page Object Model class for E2E tests.

This module provides the foundation for all page objects used in E2E testing.
"""

from typing import Any

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class BasePage:
    """
    Base class for all Page Object Model classes.

    Provides common functionality for interacting with web pages.
    """

    def __init__(self, driver: WebDriver, base_url: str):
        """
        Initialize the base page.

        Args:
            driver: Selenium WebDriver instance
            base_url: Base URL of the application
        """
        self.driver = driver
        self.base_url = base_url
        self.timeout = 10  # Default timeout in seconds

    def navigate_to(self, path: str = "") -> None:
        """
        Navigate to a specific path relative to base URL.

        Args:
            path: Path to navigate to (e.g., "/dashboard")
        """
        url = f"{self.base_url}{path}"
        self.driver.get(url)

    def find_element(
        self, by: By, value: str, timeout: int | None = None
    ) -> WebElement:
        """
        Find a single element with explicit wait.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Optional custom timeout

        Returns:
            WebElement if found

        Raises:
            TimeoutException: If element not found within timeout
        """
        wait_time = timeout if timeout is not None else self.timeout
        return WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located((by, value))
        )

    def find_elements(self, by: By, value: str) -> list[WebElement]:
        """
        Find multiple elements.

        Args:
            by: Selenium By locator strategy
            value: Locator value

        Returns:
            List of WebElements
        """
        return self.driver.find_elements(by, value)

    def click(self, by: By, value: str, timeout: int | None = None) -> None:
        """
        Click an element with explicit wait.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Optional custom timeout
        """
        wait_time = timeout if timeout is not None else self.timeout
        element = WebDriverWait(self.driver, wait_time).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()

    def send_keys(
        self, by: By, value: str, text: str, timeout: int | None = None
    ) -> None:
        """
        Send keys to an input element.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            text: Text to send
            timeout: Optional custom timeout
        """
        element = self.find_element(by, value, timeout)
        element.clear()
        element.send_keys(text)

    def get_text(self, by: By, value: str, timeout: int | None = None) -> str:
        """
        Get text from an element.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Optional custom timeout

        Returns:
            Text content of the element
        """
        element = self.find_element(by, value, timeout)
        return element.text

    def is_element_present(self, by: By, value: str, timeout: int = 2) -> bool:
        """
        Check if an element is present on the page.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Custom timeout (default 2 seconds)

        Returns:
            True if element is present, False otherwise
        """
        try:
            self.find_element(by, value, timeout)
            return True
        except TimeoutException:
            return False

    def is_element_visible(self, by: By, value: str, timeout: int = 2) -> bool:
        """
        Check if an element is visible on the page.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Custom timeout (default 2 seconds)

        Returns:
            True if element is visible, False otherwise
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def wait_for_element_to_disappear(
        self, by: By, value: str, timeout: int | None = None
    ) -> bool:
        """
        Wait for an element to disappear from the page.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Optional custom timeout

        Returns:
            True if element disappeared, False if still present
        """
        wait_time = timeout if timeout is not None else self.timeout
        try:
            WebDriverWait(self.driver, wait_time).until(
                EC.invisibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def get_attribute(
        self, by: By, value: str, attribute: str, timeout: int | None = None
    ) -> str | None:
        """
        Get an attribute value from an element.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            attribute: Attribute name
            timeout: Optional custom timeout

        Returns:
            Attribute value or None if not found
        """
        element = self.find_element(by, value, timeout)
        return element.get_attribute(attribute)

    def execute_script(self, script: str, *args: Any) -> Any:
        """
        Execute JavaScript in the browser.

        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script

        Returns:
            Return value from the script
        """
        return self.driver.execute_script(script, *args)

    def get_current_url(self) -> str:
        """
        Get the current URL.

        Returns:
            Current URL
        """
        return self.driver.current_url

    def get_page_title(self) -> str:
        """
        Get the page title.

        Returns:
            Page title
        """
        return self.driver.title
