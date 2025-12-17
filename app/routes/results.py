"""
Results page route handler for LifeFinances app.
"""

from flask import render_template, session
import pandas as pd


class ResultsPage:
    """
    A class representing the results page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the results page.
    """

    def __init__(self):
        # Retrieve results from session
        self._first_results_table = self._generate_results_table()
        self._success_percentage = session.get("success_percentage")

    def _generate_results_table(self) -> str | None:
        """
        Generate HTML table from session data.

        Returns:
            str | None: HTML table string or None if no data available.
        """
        first_results_data = session.get("first_results_data")
        first_results_columns = session.get("first_results_columns")

        if first_results_data is None or first_results_columns is None:
            return None

        # Reconstruct DataFrame from dict
        df = pd.DataFrame(first_results_data, columns=first_results_columns)

        # Generate HTML table with styling
        return df.to_html(classes="table table-striped", index=False)

    @property
    def template(self):
        """Render the results page template"""
        return render_template(
            "results.html",
            first_results_table=self._first_results_table,
            success_percentage=self._success_percentage,
        )
