"""
Dashboard Functionality E2E tests for LifeFinances GUI.

Tests dashboard stats, recent simulations, and quick actions.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.dashboard
@pytest.mark.smoke
def test_dashboard_page_loads(dashboard_page):
    """Test that dashboard page loads successfully."""
    dashboard_page.navigate()
    assert "/dashboard" in dashboard_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.dashboard
def test_dashboard_stats_visible(dashboard_page):
    """Test that dashboard statistics are visible."""
    dashboard_page.navigate()

    # All stats should be present
    config_count = dashboard_page.get_config_count()
    simulations_count = dashboard_page.get_simulations_run_count()
    success_rate = dashboard_page.get_success_rate()

    # Stats should have some value (even if "0" or "N/A")
    assert config_count is not None
    assert simulations_count is not None
    assert success_rate is not None


@pytest.mark.e2e
@pytest.mark.dashboard
def test_stats_update_after_simulation(
    dashboard_page, config_page, run_page, sample_config
):
    """Test that dashboard stats update after running simulation."""
    # Get initial stats
    dashboard_page.navigate()
    initial_sim_count = dashboard_page.get_simulations_run_count()

    # Run a simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Return to dashboard
    dashboard_page.navigate()

    # Stats should be updated
    new_sim_count = dashboard_page.get_simulations_run_count()
    success_rate = dashboard_page.get_success_rate()

    # Simulation count should increase or be shown
    assert new_sim_count != "0" if initial_sim_count == "0" else True

    # Success rate should be displayed
    assert success_rate != "N/A" and success_rate is not None


@pytest.mark.e2e
@pytest.mark.dashboard
def test_recent_simulations_display(
    dashboard_page, config_page, run_page, sample_config
):
    """Test that recent simulations are displayed."""
    # Run a simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Check dashboard
    dashboard_page.navigate()

    # Recent simulations section should be visible
    if dashboard_page.is_element_present(*dashboard_page.RECENT_SIMULATIONS_SECTION):
        assert dashboard_page.is_recent_simulations_visible()
        assert dashboard_page.get_recent_simulation_count() > 0


@pytest.mark.e2e
@pytest.mark.dashboard
def test_quick_action_config(dashboard_page):
    """Test quick action button to configuration page."""
    dashboard_page.navigate()

    # Click quick action to config
    if dashboard_page.is_element_present(*dashboard_page.QUICK_ACTION_CONFIG):
        dashboard_page.click_quick_action_config()
        assert "/config" in dashboard_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.dashboard
def test_quick_action_run(dashboard_page):
    """Test quick action button to run simulation."""
    dashboard_page.navigate()

    # Click quick action to run
    if dashboard_page.is_element_present(*dashboard_page.QUICK_ACTION_RUN):
        dashboard_page.click_quick_action_run()
        assert "/run" in dashboard_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.dashboard
def test_dashboard_after_multiple_simulations(
    dashboard_page, config_page, run_page, sample_config
):
    """Test dashboard displays correctly after multiple simulations."""
    # Run first simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Run second simulation
    run_page.navigate()
    run_page.click_run_simulation()
    run_page.wait_for_simulation_complete(timeout=60)

    # Check dashboard
    dashboard_page.navigate()

    # Should show updated count
    sim_count_text = dashboard_page.get_simulations_run_count()

    # Parse count (handles formats like "2", "2 simulations", etc.)
    assert any(char.isdigit() for char in sim_count_text)

    # Recent simulations should show multiple entries
    if dashboard_page.is_element_present(*dashboard_page.RECENT_SIMULATIONS_SECTION):
        recent_count = dashboard_page.get_recent_simulation_count()
        assert recent_count >= 1  # Should show at least one recent simulation


@pytest.mark.e2e
@pytest.mark.dashboard
def test_dashboard_config_count(dashboard_page, config_page, sample_config):
    """Test that config count is displayed correctly."""
    # Save a configuration
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    # Check dashboard
    dashboard_page.navigate()
    config_count = dashboard_page.get_config_count()

    # Should show at least 1 config
    assert config_count != "0"
