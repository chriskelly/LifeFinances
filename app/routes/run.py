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
        results = gen_simulation_results()
        first_results = results.as_dataframes()[0]
        first_results_table = first_results.to_html(classes="table table-striped")
        success_percentage = results.calc_success_percentage()

        # TODO: In Phase F5, store results in session or database
        # For now, we'll need to pass via session or store temporarily
        # Redirecting to results page
        from flask import session
        session["first_results_table"] = first_results_table
        session["success_percentage"] = success_percentage

        self._redirect_to = "results"
