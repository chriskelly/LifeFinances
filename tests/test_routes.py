"""Testing for Flask routes

Route locations
    app/__init__.py
    app/routes/index.py
    app/routes/dashboard.py
    app/routes/config.py
    app/routes/run.py
    app/routes/results.py
    app/routes/api.py
"""
from flask.testing import FlaskClient


def test_routes(client: FlaskClient):
    """Ensure all routes are working"""
    routes = [
        "/",
        "/dashboard",
        "/config",
        "/run",
        "/results",
    ]
    valid_status_codes = {200, 302}
    for route in routes:
        response = client.get(route)
        assert response.status_code in valid_status_codes


def test_dashboard_page_loads(client: FlaskClient):
    """Test that dashboard page loads successfully"""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"LifeFinances" in response.data


def test_config_page_loads(client: FlaskClient):
    """Test that config page loads successfully"""
    response = client.get("/config")
    assert response.status_code == 200
    assert b"Configuration" in response.data or b"Edit Config" in response.data


def test_config_page_save(client: FlaskClient):
    """Test that config page can save configuration"""
    # Use a valid minimal config
    test_config = """age: 30

spending:
  profiles:
    - yearly_amount: 60

portfolio:
  current_net_worth: 250
  allocation_strategy:
    flat:
      chosen: true
      allocation:
        US_Bond: 0.4
        US_Stock: 0.6
"""
    response = client.post(
        "/config", data={"edited_config": test_config, "save": "Save"}
    )
    # Should redirect or return 200
    assert response.status_code in {200, 302}


def test_run_page_loads(client: FlaskClient):
    """Test that run simulation page loads successfully"""
    response = client.get("/run")
    assert response.status_code == 200
    assert b"Simulation" in response.data or b"Run" in response.data


def test_run_page_simulation(client: FlaskClient):
    """Test that run page can execute simulation"""
    with client.session_transaction() as sess:
        # Clear any existing session data
        sess.clear()

    response = client.post("/run", data={"run_simulation": "Run"})
    # Should redirect to results page
    assert response.status_code == 302
    assert "/results" in response.location


def test_results_page_loads(client: FlaskClient):
    """Test that results page loads successfully"""
    response = client.get("/results")
    assert response.status_code == 200
    assert b"Results" in response.data or b"Simulation Results" in response.data


def test_results_page_with_data(client: FlaskClient):
    """Test that results page displays simulation data when available"""
    with client.session_transaction() as sess:
        # Store data as dict (new format to avoid cookie size limits)
        sess["first_results_data"] = [
            {"Date": "2024-01-01", "Net_Worth": 100},
            {"Date": "2024-04-01", "Net_Worth": 105},
        ]
        sess["first_results_columns"] = ["Date", "Net_Worth"]
        sess["success_percentage"] = 85

    response = client.get("/results")
    assert response.status_code == 200
    assert b"Net_Worth" in response.data or b"Net Worth" in response.data
    assert b"85" in response.data


def test_navigation_links(client: FlaskClient):
    """Test that navigation links are present in pages"""
    pages = ["/dashboard", "/config", "/run"]

    for page in pages:
        response = client.get(page)
        assert response.status_code == 200
        # Check for navigation links
        assert b"Dashboard" in response.data
        assert b"Configuration" in response.data or b"Config" in response.data


def test_index_redirects_to_dashboard(client: FlaskClient):
    """Test that index page exists (legacy support)"""
    response = client.get("/")
    # Index page should still work for backward compatibility
    assert response.status_code in {200, 302}


def test_results_page_charts(client: FlaskClient):
    """Test that results page includes Plotly visualizations"""
    with client.session_transaction() as sess:
        # Store data as dict (new format to avoid cookie size limits)
        sess["first_results_data"] = [
            {"Date": "2024-01-01", "Net_Worth": 100},
            {"Date": "2024-04-01", "Net_Worth": 105},
        ]
        sess["first_results_columns"] = ["Date", "Net_Worth"]
        sess["success_percentage"] = 85

    response = client.get("/results")
    assert response.status_code == 200

    # Check for Plotly.js CDN
    assert b"plotly" in response.data or b"Plotly" in response.data

    # Check for div elements for charts
    assert b"successGauge" in response.data
    assert b"netWorthChart" in response.data

    # Check for visualization elements
    assert b"Success Rate" in response.data
    assert b"Key Metrics" in response.data
    assert b"Net Worth Projection" in response.data


def test_results_page_export_button(client: FlaskClient):
    """Test that results page includes CSV export functionality"""
    with client.session_transaction() as sess:
        # Store data as dict (new format to avoid cookie size limits)
        sess["first_results_data"] = [
            {"Date": "2024-01-01", "Net_Worth": 100},
            {"Date": "2024-04-01", "Net_Worth": 105},
        ]
        sess["first_results_columns"] = ["Date", "Net_Worth"]
        sess["success_percentage"] = 75

    response = client.get("/results")
    assert response.status_code == 200

    # Check for export button
    assert b"Export CSV" in response.data
    assert b"btnExportCSV" in response.data


def test_results_page_interpretation(client: FlaskClient):
    """Test that results page provides interpretation of success rate"""
    # Test excellent success rate
    with client.session_transaction() as sess:
        # Store data as dict (new format to avoid cookie size limits)
        sess["first_results_data"] = [
            {"Date": "2024-01-01", "Net_Worth": 100},
            {"Date": "2024-04-01", "Net_Worth": 105},
        ]
        sess["first_results_columns"] = ["Date", "Net_Worth"]
        sess["success_percentage"] = 90

    response = client.get("/results")
    assert b"high probability" in response.data
    assert b"Excellent" in response.data

    # Test moderate success rate
    with client.session_transaction() as sess:
        sess["first_results_data"] = [
            {"Date": "2024-01-01", "Net_Worth": 100},
            {"Date": "2024-04-01", "Net_Worth": 105},
        ]
        sess["first_results_columns"] = ["Date", "Net_Worth"]
        sess["success_percentage"] = 65

    response = client.get("/results")
    assert b"moderate probability" in response.data
    assert b"Moderate" in response.data

    # Test low success rate
    with client.session_transaction() as sess:
        sess["first_results_data"] = [
            {"Date": "2024-01-01", "Net_Worth": 100},
            {"Date": "2024-04-01", "Net_Worth": 105},
        ]
        sess["first_results_columns"] = ["Date", "Net_Worth"]
        sess["success_percentage"] = 40

    response = client.get("/results")
    assert b"low probability" in response.data
    assert b"Low" in response.data
