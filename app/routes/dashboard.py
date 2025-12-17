"""
Dashboard page route handler for LifeFinances app.
"""

from flask import render_template
from app.models.config import read_config_file


class DashboardPage:
    """
    A class representing the dashboard page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the dashboard page.
    """

    def __init__(self):
        self._config = read_config_file()
        self._stats = self._get_stats()

    @property
    def template(self):
        """Render the dashboard page template"""
        return render_template("dashboard.html", stats=self._stats)

    def _get_stats(self) -> dict:
        """
        Get dashboard statistics.

        Returns:
            dict: Statistics including config count, simulations run, and success rate.
        """
        # TODO: In future phases, this will read from a database or session
        # For now, return placeholder values
        return {
            "config_count": 1 if self._config else 0,
            "simulations_run": 0,
            "success_rate": None,
        }
