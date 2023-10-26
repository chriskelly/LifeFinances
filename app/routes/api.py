"""API Endpoints"""
from flask import Blueprint, render_template
from app.models.simulator import SimulationEngine

api = Blueprint("api", __name__)


@api.route("simulation")
def run_simulation():
    """Run the simulation"""
    engine = SimulationEngine()
    engine.gen_all_trials()
    df = engine.results.as_dataframes()[0]
    success_rate = round(engine.results.success_rate(), ndigits=1)
    return render_template(
        "simulation.html",
        table=df.to_html(classes="table table-striped"),
        success_rate=success_rate,
    )
