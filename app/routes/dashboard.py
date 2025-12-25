"""
Dashboard page route handler for LifeFinances app.
"""

from flask import render_template, session

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
        self._recent_simulations = self._get_recent_simulations()

    @property
    def template(self):
        """Render the dashboard page template"""
        return render_template(
            "dashboard.html",
            stats=self._stats,
            recent_simulations=self._recent_simulations,
            has_config=self._config is not None,
        )

    def _get_stats(self) -> dict:
        """
        Get dashboard statistics from session.

        Returns:
            dict: Statistics including config count, simulations run, and success rate.
        """
        simulation_history = session.get("simulation_history", [])

        # Calculate stats from session history
        simulations_run = len(simulation_history)
        latest_success_rate = None

        if simulation_history:
            latest_success_rate = simulation_history[-1].get("success_percentage")
            # Convert to float if it's a string (Flask-Session serialization)
            if latest_success_rate is not None and isinstance(latest_success_rate, str):
                latest_success_rate = float(latest_success_rate)

        return {
            "config_count": 1 if self._config else 0,
            "simulations_run": simulations_run,
            "success_rate": latest_success_rate,
        }

    def _get_recent_simulations(self) -> list:
        """
        Get recent simulation results from session.

        Returns:
            list: List of recent simulation results (up to 5 most recent).
        """
        simulation_history = session.get("simulation_history", [])

        # Convert success_percentage to float if it's a string (Flask-Session serialization)
        normalized_history = []
        for sim in simulation_history:
            sim_copy = sim.copy()
            success_pct = sim_copy.get("success_percentage")
            if success_pct is not None and isinstance(success_pct, str):
                sim_copy["success_percentage"] = float(success_pct)
            normalized_history.append(sim_copy)

        # Return up to 5 most recent simulations
        return list(reversed(normalized_history[-5:]))
