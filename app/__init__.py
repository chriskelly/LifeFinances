"""Flask app definition"""

# Allow importing app modules without initializing Flask app
# This prevents circular import issues when using app modules in notebooks/scripts
import os
_skip_flask_init = os.environ.get("SKIP_FLASK_INIT", "0") == "1"

if not _skip_flask_init:
    from flask import Flask, request
    from app.routes.api import api as api_blueprint
    from app.routes.index import IndexPage


def create_app():
    """Create the Flask app with index route"""
    if _skip_flask_init:
        raise RuntimeError("Flask app initialization is disabled (SKIP_FLASK_INIT=1)")

    app = Flask(__name__)
    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.route("/", methods=["GET", "POST"])
    def index():
        index_page = IndexPage(request)
        return index_page.template

    return app
