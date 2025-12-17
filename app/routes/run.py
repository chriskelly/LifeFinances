"""
Run simulation page route handler for LifeFinances app.
"""

from flask import Request, render_template, redirect, url_for
from app.models.config import read_config_file
from app.models.simulator import gen_simulation_results


class RunPage:
    """
    A class representing the run simulation page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the run page.
    """

    def __init__(self, req: Request):
        self._config = read_config_file()
        self._redirect_to = None

        if req.method == "POST":
            self._handle_form()

    @property
    def template(self):
        """Render the run page template or redirect"""
        if self._redirect_to:
            return redirect(url_for(self._redirect_to))
        return render_template("run.html", config=self._config)

    def _handle_form(self):
        """
        Handle form submission for running simulation.
        Runs the simulation and redirects to results page.
        """
        from datetime import datetime
        from flask import session

        results = gen_simulation_results()
        first_results = results.as_dataframes()[0]
        success_percentage = results.calc_success_percentage()

        # Store only essential data in session (not full HTML table to avoid cookie size limits)
        # Convert DataFrame to dict for JSON serialization
        session["first_results_data"] = first_results.to_dict(orient="records")
        session["first_results_columns"] = first_results.columns.tolist()
        session["success_percentage"] = success_percentage

        # Add to simulation history
        if "simulation_history" not in session:
            session["simulation_history"] = []

        simulation_record = {
            "timestamp": datetime.now().isoformat(),
            "success_percentage": success_percentage,
            "trial_count": 500,  # Default trial count
        }

        session["simulation_history"].append(simulation_record)

        # Keep only last 10 simulations to avoid session bloat
        if len(session["simulation_history"]) > 10:
            session["simulation_history"] = session["simulation_history"][-10:]

        session.modified = True

        self._redirect_to = "results"
