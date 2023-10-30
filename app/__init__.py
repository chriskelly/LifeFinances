"""Flask app definition"""

from flask import Flask, redirect, url_for
from app.routes.api import api as api_blueprint


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.route("/")
    def redirect_to_simulation():
        return redirect(url_for("api.run_simulation"))

    return app
