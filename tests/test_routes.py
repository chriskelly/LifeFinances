"""Testing for Flask routes

Route locations
    app/__init__.py
    
    app/routes/api.py
"""
# pylint:disable=redefined-outer-name
import pytest


@pytest.fixture
def routes_to_test() -> dict:
    """Returns dictionary of `route:expected_response`"""
    return {
        "/": "Hello, World!",
        "/api/simulation": "Here's the simulation!",
    }


def test_routes(client, routes_to_test: dict):
    """Ensure all routes are working"""
    for route, expected_res in routes_to_test.items():
        response = client.get(route)
        assert response.status_code == 200
        assert expected_res.encode("utf-8") in response.data
