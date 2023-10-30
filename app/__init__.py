"""Flask app definition"""

from flask import Flask
from app.routes.api import api as api_blueprint


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.route("/")
    def hello():
        return "Hello, World!"

    return app
