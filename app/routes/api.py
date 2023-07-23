"""API Endpoints"""
from flask import Blueprint

api = Blueprint("api", __name__)


@api.route("simulation")
def run_simulation():
    pass
