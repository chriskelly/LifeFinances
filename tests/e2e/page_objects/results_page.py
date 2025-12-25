"""Results Page Object Model for E2E tests."""
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.select import Select

from tests.e2e.page_objects.base_page import BasePage


class ResultsPage(BasePage):
    """Page Object for the Results page."""

    # Locators
    SUCCESS_GAUGE = (By.ID, "success-gauge")
    NET_WORTH_CHART = (By.ID, "net-worth-chart")
    CUSTOM_CHART = (By.ID, "custom-chart")

    VARIABLE_SELECTOR = (By.ID, "variable-selector")
    LOG_SCALE_CHECKBOX = (By.ID, "log-scale-toggle")
    UPDATE_CHART_BUTTON = (By.ID, "update-chart")

    RESULTS_TABLE = (By.ID, "results-table")
    EXPORT_CSV_BUTTON = (By.ID, "export-csv")
    EXPORT_EXCEL_BUTTON = (By.ID, "export-excel")

    INTERPRETATION_SECTION = (By.ID, "interpretation")
    INTERPRETATION_TEXT = (By.CSS_SELECTOR, "#interpretation p")

    NO_RESULTS_MESSAGE = (By.CSS_SELECTOR, ".no-results")

    def __init__(self, driver: WebDriver, base_url: str):
        """Initialize Results page."""
        super().__init__(driver, base_url)
        self.path = "/results"

    def navigate(self) -> None:
        """Navigate to results page."""
        self.navigate_to(self.path)

    def is_success_gauge_visible(self) -> bool:
        """
        Check if success rate gauge chart is visible.

        Returns:
            True if gauge is visible, False otherwise
        """
        return self.is_element_visible(*self.SUCCESS_GAUGE)

    def is_net_worth_chart_visible(self) -> bool:
        """
        Check if net worth chart is visible.

        Returns:
            True if chart is visible, False otherwise
        """
        return self.is_element_visible(*self.NET_WORTH_CHART)

    def is_custom_chart_visible(self) -> bool:
        """
        Check if custom variable chart is visible.

        Returns:
            True if chart is visible, False otherwise
        """
        return self.is_element_visible(*self.CUSTOM_CHART)

    def select_variable(self, variable_name: str) -> None:
        """
        Select a variable from the dropdown.

        Args:
            variable_name: Name of the variable to select
        """
        select_element = Select(self.find_element(*self.VARIABLE_SELECTOR))
        select_element.select_by_visible_text(variable_name)

    def toggle_log_scale(self) -> None:
        """Toggle the log scale checkbox."""
        self.click(*self.LOG_SCALE_CHECKBOX)

    def is_log_scale_checked(self) -> bool:
        """
        Check if log scale checkbox is checked.

        Returns:
            True if checked, False otherwise
        """
        element = self.find_element(*self.LOG_SCALE_CHECKBOX)
        return element.is_selected()

    def click_update_chart(self) -> None:
        """Click the Update Chart button."""
        self.click(*self.UPDATE_CHART_BUTTON)

    def is_results_table_visible(self) -> bool:
        """
        Check if results table is visible.

        Returns:
            True if table is visible, False otherwise
        """
        return self.is_element_visible(*self.RESULTS_TABLE)

    def get_table_row_count(self) -> int:
        """
        Get the number of rows in the results table.

        Returns:
            Number of table rows (excluding header)
        """
        rows = self.find_elements(By.CSS_SELECTOR, "#results-table tbody tr")
        return len(rows)

    def click_export_csv(self) -> None:
        """Click the Export CSV button."""
        self.click(*self.EXPORT_CSV_BUTTON)

    def click_export_excel(self) -> None:
        """Click the Export Excel button."""
        self.click(*self.EXPORT_EXCEL_BUTTON)

    def is_interpretation_visible(self) -> bool:
        """
        Check if interpretation section is visible.

        Returns:
            True if interpretation is visible, False otherwise
        """
        return self.is_element_visible(*self.INTERPRETATION_SECTION)

    def get_interpretation_text(self) -> str:
        """
        Get the interpretation text.

        Returns:
            Interpretation text content
        """
        return self.get_text(*self.INTERPRETATION_TEXT)

    def is_no_results_message_visible(self) -> bool:
        """
        Check if 'no results' message is visible.

        Returns:
            True if message is visible, False otherwise
        """
        return self.is_element_visible(*self.NO_RESULTS_MESSAGE)

    def get_chart_data_points(self, chart_id: str) -> int:
        """
        Get the number of data points in a Plotly chart using JavaScript.

        Args:
            chart_id: ID of the chart element

        Returns:
            Number of data points in the first trace
        """
        script = f"""
        const chartDiv = document.getElementById('{chart_id}');
        if (chartDiv && chartDiv.data && chartDiv.data[0]) {{
            return chartDiv.data[0].x.length;
        }}
        return 0;
        """
        return self.execute_script(script)

    def is_chart_interactive(self, chart_id: str) -> bool:
        """
        Check if a Plotly chart has interactive features enabled.

        Args:
            chart_id: ID of the chart element

        Returns:
            True if chart is interactive, False otherwise
        """
        script = f"""
        const chartDiv = document.getElementById('{chart_id}');
        if (chartDiv && chartDiv.layout) {{
            return chartDiv.layout.hovermode !== false;
        }}
        return false;
        """
        return self.execute_script(script)
