"""Flask app definition"""


def create_app():
    """Create the Flask app with all routes"""
    # Import here to avoid circular deps
    import logging

    from flask import Flask, request

    from app.routes.api import api as api_blueprint
    from app.routes.config import ConfigPage
    from app.routes.dashboard import DashboardPage
    from app.routes.index import IndexPage
    from app.routes.results import ResultsPage
    from app.routes.run import RunPage
    from flask_session import Session

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = Flask(__name__)
    app.secret_key = "lifefinances-secret-key-change-in-production"  # TODO: Move to env var

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
        # Redirect root to dashboard for modern UI
        from flask import redirect, url_for
        return redirect(url_for("dashboard"))

    @app.route("/dashboard", methods=["GET"])
    def dashboard():
        dashboard_page = DashboardPage()
        return dashboard_page.template

    @app.route("/config", methods=["GET", "POST"])
    def config():
        config_page = ConfigPage(request)
        return config_page.template

    @app.route("/run", methods=["GET", "POST"])
    def run():
        run_page = RunPage(request)
        return run_page.template

    @app.route("/results", methods=["GET"])
    def results():
        results_page = ResultsPage()
        return results_page.template

    return app
