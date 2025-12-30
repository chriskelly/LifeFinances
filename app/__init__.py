"""Flask app definition"""


def create_app():
    """Create the Flask app with index route"""
    # Import here to avoid circular deps
    from flask import Flask, request

    from app.routes.api import api as api_blueprint
    from app.routes.index import IndexPage
    from flask_session import Session

    app = Flask(__name__)
    # Secret key for session signing and flash messages (local dev tool)
    app.secret_key = "lifefinances-local-dev-secret"

    # Configure server-side sessions to avoid cookie size limits
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_KEY_PREFIX"] = "lifefinances:"
    app.config["SESSION_FILE_THRESHOLD"] = 500  # Max number of session files
    Session(app)

    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.route("/", methods=["GET", "POST"])
    def index():
        index_page = IndexPage(request)
        return index_page.template

    return app
