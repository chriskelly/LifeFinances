"""
Results Visualization E2E tests for LifeFinances GUI.

Tests results display, charts, table, and export functionality.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.results
@pytest.mark.smoke
def test_results_page_loads(results_page):
    """Test that results page loads successfully."""
    results_page.navigate()
    assert "/results" in results_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.results
def test_no_results_message_when_empty(results_page):
    """Test that 'no results' message shows when no simulation run."""
    results_page.navigate()
    # Either no results message or charts should be visible
    has_message = results_page.is_no_results_message_visible()
    has_charts = results_page.is_success_gauge_visible()

    # At least one should be true
    assert has_message or has_charts


@pytest.mark.e2e
@pytest.mark.results
def test_results_display_after_simulation(
    config_page, run_page, results_page, sample_config
):
    """Test that results are displayed after running simulation."""
    # Run a simulation first
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    run_page.navigate()
    run_page.click_run_simulation()
    run_page.wait_for_simulation_complete(timeout=60)

    # Should automatically be on results page
    assert "/results" in results_page.get_current_url()

    # Verify results are displayed
    assert results_page.is_success_gauge_visible()
    assert results_page.is_net_worth_chart_visible()
    assert results_page.is_results_table_visible()


@pytest.mark.e2e
@pytest.mark.results
def test_success_gauge_chart(config_page, run_page, results_page, sample_config):
    """Test that success rate gauge chart is displayed."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Verify gauge chart
    assert results_page.is_success_gauge_visible()


@pytest.mark.e2e
@pytest.mark.results
def test_net_worth_chart(config_page, run_page, results_page, sample_config):
    """Test that net worth chart is displayed with data."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Verify net worth chart
    assert results_page.is_net_worth_chart_visible()

    # Verify chart has data points
    data_points = results_page.get_chart_data_points("net-worth-chart")
    assert data_points > 0


@pytest.mark.e2e
@pytest.mark.results
def test_custom_variable_chart(config_page, run_page, results_page, sample_config):
    """Test custom variable chart selection and display."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Select a variable (if dropdown exists)
    if results_page.is_element_present(*results_page.VARIABLE_SELECTOR):
        results_page.select_variable("Spending")
        results_page.click_update_chart()

        # Verify custom chart appears
        assert results_page.is_custom_chart_visible()


@pytest.mark.e2e
@pytest.mark.results
def test_log_scale_toggle(config_page, run_page, results_page, sample_config):
    """Test log scale toggle functionality."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Toggle log scale if available
    if results_page.is_element_present(*results_page.LOG_SCALE_CHECKBOX):
        # Get initial state
        initial_state = results_page.is_log_scale_checked()

        # Toggle
        results_page.toggle_log_scale()

        # Verify state changed
        new_state = results_page.is_log_scale_checked()
        assert new_state != initial_state


@pytest.mark.e2e
@pytest.mark.results
def test_results_table_display(config_page, run_page, results_page, sample_config):
    """Test that results table displays data."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Verify table
    assert results_page.is_results_table_visible()

    # Verify table has rows
    row_count = results_page.get_table_row_count()
    assert row_count > 0


@pytest.mark.e2e
@pytest.mark.results
def test_chart_interactivity(config_page, run_page, results_page, sample_config):
    """Test that Plotly charts are interactive."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Verify charts are interactive
    assert results_page.is_chart_interactive("net-worth-chart")


@pytest.mark.e2e
@pytest.mark.results
def test_interpretation_section(config_page, run_page, results_page, sample_config):
    """Test that interpretation section is visible."""
    # Run simulation
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Check if interpretation section exists
    if results_page.is_element_present(*results_page.INTERPRETATION_SECTION):
        assert results_page.is_interpretation_visible()


@pytest.mark.e2e
@pytest.mark.results
def test_chart_with_negative_values(config_page, run_page, results_page, sample_config):
    """Test that charts display correctly with negative values."""
    # Modify config to potentially create negative values (high spending)
    modified_config = sample_config.replace(
        "annual_spending: 60000", "annual_spending: 150000"
    )

    config_page.navigate()
    config_page.set_config_content(modified_config)
    config_page.click_save_and_run()
    run_page.wait_for_simulation_complete(timeout=60)

    # Charts should still render
    assert results_page.is_net_worth_chart_visible()

    # Select spending variable if available
    if results_page.is_element_present(*results_page.VARIABLE_SELECTOR):
        results_page.select_variable("Spending")
        results_page.click_update_chart()
        assert results_page.is_custom_chart_visible()
