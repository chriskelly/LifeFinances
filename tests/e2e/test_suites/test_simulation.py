"""
Simulation Execution E2E tests for LifeFinances GUI.

Tests simulation running, progress tracking, and completion.
"""
import pytest


@pytest.mark.e2e
@pytest.mark.simulation
@pytest.mark.smoke
def test_run_page_loads(run_page):
    """Test that run simulation page loads successfully."""
    run_page.navigate()
    assert "/run" in run_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.simulation
def test_run_button_enabled(run_page):
    """Test that run simulation button is enabled when config exists."""
    run_page.navigate()
    assert run_page.is_run_button_enabled()


@pytest.mark.e2e
@pytest.mark.simulation
def test_config_preview_visible(run_page):
    """Test that configuration preview is visible on run page."""
    run_page.navigate()
    assert run_page.is_config_preview_visible()


@pytest.mark.e2e
@pytest.mark.simulation
def test_run_simulation_completes(run_page):
    """Test that simulation runs and completes successfully."""
    run_page.navigate()

    # Click run simulation
    run_page.click_run_simulation()

    # Wait for simulation to complete (max 60 seconds)
    completed = run_page.wait_for_simulation_complete(timeout=60)
    assert completed, "Simulation did not complete within 60 seconds"

    # Should redirect to results page
    assert "/results" in run_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.simulation
def test_simulation_from_config_page(config_page, sample_config):
    """Test running simulation directly from config page."""
    config_page.navigate()

    # Set configuration
    config_page.set_config_content(sample_config)

    # Click Save and Run
    config_page.click_save_and_run()

    # Should be on run page
    assert "/run" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.simulation
def test_full_simulation_workflow(config_page, run_page, sample_config):
    """Test the complete workflow from config to running simulation."""
    # Step 1: Configure
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    # Step 2: Navigate to run page
    run_page.navigate()
    assert run_page.is_run_button_enabled()

    # Step 3: Run simulation
    run_page.click_run_simulation()

    # Step 4: Wait for completion
    completed = run_page.wait_for_simulation_complete(timeout=60)
    assert completed

    # Step 5: Verify redirect to results
    assert "/results" in run_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.simulation
def test_simulation_without_config_error(run_page):
    """Test simulation behavior when no configuration exists."""
    run_page.navigate()

    # This test assumes that either:
    # 1. Run button is disabled without config, OR
    # 2. Error message is shown
    # Implementation depends on app behavior
    is_enabled = run_page.is_run_button_enabled()

    if is_enabled:
        # If button is enabled, clicking should show error
        run_page.click_run_simulation()
        # Check for error message or staying on same page
        assert (
            "/run" in run_page.get_current_url()
            or run_page.is_error_message_visible()
        )
