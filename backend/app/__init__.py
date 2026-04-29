"""Flask app definition"""

import os


def create_app():
    """Create the Flask app with API blueprint and SPA redirect."""
    # Import here to avoid circular deps
    from flask import Flask, redirect

    from app.routes.api import api as api_blueprint

    app = Flask(__name__)
    app.register_blueprint(api_blueprint, url_prefix="/api")

    frontend_redirect = os.environ.get(
        "FRONTEND_REDIRECT_URL", "http://localhost:5173/"
    )
    if not frontend_redirect.endswith("/"):
        frontend_redirect = f"{frontend_redirect}/"

    @app.route("/", methods=["GET", "POST"])
    def index():
        return redirect(frontend_redirect, code=302)

    return app
