"""
Navigation E2E tests for LifeFinances GUI.

Tests basic navigation between pages and URL verification.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.navigation
@pytest.mark.smoke
def test_navigation_to_dashboard(dashboard_page):
    """Test navigation to dashboard page."""
    dashboard_page.navigate()
    assert "/dashboard" in dashboard_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.navigation
@pytest.mark.smoke
def test_navigation_to_config(config_page):
    """Test navigation to configuration page."""
    config_page.navigate()
    assert "/config" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.navigation
@pytest.mark.smoke
def test_navigation_to_run(run_page):
    """Test navigation to run simulation page."""
    run_page.navigate()
    assert "/run" in run_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.navigation
@pytest.mark.smoke
def test_navigation_to_results(results_page):
    """Test navigation to results page."""
    results_page.navigate()
    assert "/results" in results_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.navigation
def test_navigation_links_from_dashboard(dashboard_page):
    """Test that navigation links work from dashboard."""
    dashboard_page.navigate()

    # Test navigation to config
    dashboard_page.click_navigation_config()
    assert "/config" in dashboard_page.get_current_url()

    # Return to dashboard
    dashboard_page.navigate()

    # Test navigation to run
    dashboard_page.click_navigation_run()
    assert "/run" in dashboard_page.get_current_url()

    # Return to dashboard
    dashboard_page.navigate()

    # Test navigation to results
    dashboard_page.click_navigation_results()
    assert "/results" in dashboard_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.navigation
def test_root_redirects_to_dashboard(driver, base_url):
    """Test that root URL redirects to dashboard."""
    driver.get(base_url)
    assert "/dashboard" in driver.current_url


@pytest.mark.e2e
@pytest.mark.navigation
def test_navigation_breadcrumb_trail(
    dashboard_page, config_page, run_page, results_page
):
    """Test full navigation flow through all pages."""
    # Start at dashboard
    dashboard_page.navigate()
    assert "/dashboard" in dashboard_page.get_current_url()

    # Navigate to config
    config_page.navigate()
    assert "/config" in config_page.get_current_url()

    # Navigate to run
    run_page.navigate()
    assert "/run" in run_page.get_current_url()

    # Navigate to results
    results_page.navigate()
    assert "/results" in results_page.get_current_url()

    # Navigate back to dashboard
    dashboard_page.navigate()
    assert "/dashboard" in dashboard_page.get_current_url()
