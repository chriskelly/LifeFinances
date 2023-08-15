"""API Endpoints"""
from flask import Blueprint
from app.models.simulator import SimulationEngine

api = Blueprint("api", __name__)


@api.route("simulation")
def run_simulation():
    """Run the simulation"""
    engine = SimulationEngine()
    engine.gen_all_trials()
    return "Here's the simulation!"
