"""Testing for Flask routes

Route locations
    app/__init__.py
    
    app/routes/api.py
"""


def test_index_route(client):
    """Ensure the index route is working"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hello, World!" in response.data


def test_about_route(client):
    """Ensure the simulation route is working"""
    response = client.get("/api/simulation")
    assert response.status_code == 200
    assert b"Here's the simulation!" in response.data
