"""Flask app definition"""

from flask import Flask, redirect, render_template, request, url_for
import pandas as pd
from app.models.simulator import SimulationEngine
from app.routes.api import api as api_blueprint


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.route("/", methods=["GET", "POST"])
    def index():
        df = pd.DataFrame()
        success_percentage = ""
        if request.method == "POST":
            edited_config = request.form["edited_config"]
            with open("config.yml", "w") as config_file:
                config_file.write(edited_config)
            if "run_simulation" in request.form:
                engine = SimulationEngine()
                engine.gen_all_trials()
                df = engine.results.as_dataframes()[0]
                success_percentage = round(
                    100 * engine.results.success_rate(), ndigits=1
                )
        with open("config.yml", "r") as config_file:
            config = config_file.read()
        return render_template(
            "index.html",
            config=config,
            table=df.to_html(classes="table table-striped"),
            success_percentage=success_percentage,
        )

    return app
