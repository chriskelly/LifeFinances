"""Flask app definition"""

def create_app():
    """Create the Flask app with all routes"""
    # pylint: disable=import-outside-toplevel

    # Import here to avoid circular deps
    from flask import Flask, request
    from app.routes.api import api as api_blueprint
    from app.routes.index import IndexPage
    from app.routes.dashboard import DashboardPage
    from app.routes.config import ConfigPage
    from app.routes.run import RunPage
    from app.routes.results import ResultsPage

    app = Flask(__name__)
    app.secret_key = "lifefinances-secret-key-change-in-production"  # TODO: Move to env var
    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.route("/", methods=["GET", "POST"])
    def index():
        index_page = IndexPage(request)
        return index_page.template

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
