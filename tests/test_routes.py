"""Testing for Flask routes

Route locations
    app/__init__.py
    
    app/routes/api.py
"""
from flask.testing import FlaskClient


def test_routes(client: FlaskClient):
    """Ensure all routes are working"""
    routes = [
        "/",
        "/api/simulation",
    ]
    valid_status_codes = {200, 302}
    for route in routes:
        response = client.get(route)
        assert response.status_code in valid_status_codes
