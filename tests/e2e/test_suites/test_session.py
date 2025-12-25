"""
Session Persistence E2E tests for LifeFinances GUI.

Tests session data persistence across page navigation and reloads.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.session
def test_config_persists_across_pages(config_page, dashboard_page, sample_config):
    """Test that configuration persists when navigating between pages."""
    # Save config
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    # Navigate away
    dashboard_page.navigate()

    # Return to config
    config_page.navigate()

    # Config should still be there
    content = config_page.get_config_content()
    assert "Test User" in content


@pytest.mark.e2e
@pytest.mark.session
def test_results_persist_after_navigation(
    config_page, run_page, results_page, dashboard_page, sample_config
):
    """Test that simulation results persist after navigating away."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Verify results are shown
    assert results_page.is_success_gauge_visible()

    # Navigate away to dashboard
    dashboard_page.navigate()

    # Navigate back to results
    results_page.navigate()

    # Results should still be visible
    assert results_page.is_success_gauge_visible()
    assert results_page.is_net_worth_chart_visible()


@pytest.mark.e2e
@pytest.mark.session
def test_simulation_history_persists(
    config_page, run_page, dashboard_page, sample_config
):
    """Test that simulation history is maintained in session."""
    # Run first simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Go to dashboard
    dashboard_page.navigate()
    first_count = dashboard_page.get_simulations_run_count()

    # Run second simulation
    run_page.navigate()
    run_page.click_run_simulation()
    run_page.wait_for_simulation_complete(timeout=60)

    # Check dashboard again
    dashboard_page.navigate()
    second_count = dashboard_page.get_simulations_run_count()

    # Count should have increased
    # Parse numbers from strings for comparison
    first_num = int("".join(filter(str.isdigit, first_count)) or "0")
    second_num = int("".join(filter(str.isdigit, second_count)) or "0")

    assert second_num > first_num


@pytest.mark.e2e
@pytest.mark.session
def test_page_reload_maintains_session(config_page, driver, sample_config):
    """Test that browser page reload maintains session data."""
    # Save config
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    # Reload the page
    driver.refresh()

    # Config should still be there after reload
    content = config_page.get_config_content()
    assert "Test User" in content


@pytest.mark.e2e
@pytest.mark.session
def test_results_persist_after_page_reload(
    config_page, run_page, results_page, driver, sample_config
):
    """Test that results persist after page reload."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Verify results
    assert results_page.is_success_gauge_visible()

    # Reload the page
    driver.refresh()

    # Results should still be visible
    assert results_page.is_success_gauge_visible()


@pytest.mark.e2e
@pytest.mark.session
def test_session_isolation_between_tabs(config_page, driver, base_url, sample_config):
    """Test that session is shared across browser tabs."""
    # Save config in first tab
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    # Open new tab
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[1])

    # Navigate to config in new tab
    driver.get(f"{base_url}/config")

    # Config should be available in new tab (same session)
    from tests.e2e.page_objects.config_page import ConfigPage

    new_tab_config_page = ConfigPage(driver, base_url)
    content = new_tab_config_page.get_config_content()

    # Session data should be shared
    assert "Test User" in content

    # Close the second tab
    driver.close()
    driver.switch_to.window(driver.window_handles[0])


@pytest.mark.e2e
@pytest.mark.session
def test_full_workflow_session_persistence(
    config_page, run_page, results_page, dashboard_page, sample_config
):
    """Test complete workflow with session persistence at each step."""
    # Step 1: Save config
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    # Navigate away and back
    dashboard_page.navigate()
    config_page.navigate()
    assert "Test User" in config_page.get_config_content()

    # Step 2: Run simulation
    run_page.navigate()
    run_page.click_run_simulation()
    run_page.wait_for_simulation_complete(timeout=60)

    # Step 3: View results
    assert results_page.is_success_gauge_visible()

    # Step 4: Navigate to dashboard
    dashboard_page.navigate()
    sim_count = dashboard_page.get_simulations_run_count()
    assert sim_count != "0"

    # Step 5: Return to results
    results_page.navigate()
    assert results_page.is_success_gauge_visible()

    # Step 6: Return to config
    config_page.navigate()
    assert "Test User" in config_page.get_config_content()
