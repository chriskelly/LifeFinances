"""
Results page route handler for LifeFinances app.
"""

from flask import render_template, session


class ResultsPage:
    """
    A class representing the results page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the results page.
    """

    def __init__(self):
        # Retrieve results from session
        # TODO: In Phase F5, implement proper result storage (database or persistent session)
        self._first_results_table = session.get("first_results_table", "")
        self._success_percentage = session.get("success_percentage", "")

    @property
    def template(self):
        """Render the results page template"""
        return render_template(
            "results.html",
            first_results_table=self._first_results_table,
            success_percentage=self._success_percentage,
        )
