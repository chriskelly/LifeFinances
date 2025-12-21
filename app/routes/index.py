"""
This module contains the IndexPage class, which represents the index page of the LifeFinances app.
It also contains functions for reading and writing configuration files,
and generating simulation results.
"""

from flask import Request, render_template

from app.models.config import read_config_file, write_config_file
from app.models.simulator import gen_simulation_results


class IndexPage:
    """
    A class representing the index page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the index page.
    """

    def __init__(self, req: Request):
        self._first_results_table = ""
        self._success_percentage = ""
        if req.method == "POST":
            self._handle_form(req.form)
        self._config = read_config_file()

    @property
    def template(self):
        """Render the index page template"""
        return render_template(
            "index.html",
            config=self._config,
            first_results_table=self._first_results_table,
            success_percentage=self._success_percentage,
        )

    def _handle_form(self, form: dict[str, str]):
        write_config_file(form["edited_config"])
        if "run_simulation" in form:
            self._update_simulation_results()

    def _update_simulation_results(self):
        results = gen_simulation_results()
        first_results = results.as_dataframes()[0]
        self._first_results_table = first_results.to_html(classes="table table-striped")
        self._success_percentage = results.calc_success_percentage()
