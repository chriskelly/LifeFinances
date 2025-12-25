"""
Configuration page route handler for LifeFinances app.
"""

from flask import Request, redirect, render_template, url_for

from app.models.config import read_config_file, write_config_file


class ConfigPage:
    """
    A class representing the configuration page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the config page.
    """

    def __init__(self, req: Request):
        self._redirect_to = None
        if req.method == "POST":
            self._handle_form(req.form)
        self._config = read_config_file()

    @property
    def template(self):
        """Render the config page template or redirect"""
        if self._redirect_to:
            return redirect(url_for(self._redirect_to))
        return render_template("config.html", config=self._config)

    def _handle_form(self, form: dict[str, str]):
        """
        Handle form submission for saving configuration.

        Args:
            form: Form data from the request.
        """
        write_config_file(form["edited_config"])
        if "run_simulation" in form:
            # Redirect to run page after saving if run_simulation was clicked
            self._redirect_to = "run"
        else:
            # Redirect back to config page after saving
            self._redirect_to = "config"
