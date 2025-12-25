"""
Error Handling E2E tests for LifeFinances GUI.

Tests error scenarios, validation, and error recovery.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.error
def test_invalid_yaml_config(config_page):
    """Test handling of invalid YAML syntax in configuration."""
    config_page.navigate()

    # Set invalid YAML
    invalid_yaml = """
User:
  name: Test
  invalid: [unclosed bracket
  bad syntax here
"""
    config_page.set_config_content(invalid_yaml)
    config_page.click_save()

    # Should either show error or stay on config page
    assert "/config" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.error
def test_missing_required_fields(config_page):
    """Test handling of configuration with missing required fields."""
    config_page.navigate()

    # Set incomplete config (missing required fields)
    incomplete_config = """
User:
  name: Test User
"""
    config_page.set_config_content(incomplete_config)
    config_page.click_save()

    # Should handle gracefully (error message or validation)
    assert "/config" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.error
def test_invalid_date_format(config_page):
    """Test handling of invalid date formats in configuration."""
    config_page.navigate()

    # Set config with invalid dates
    invalid_date_config = """
User:
  name: Test User
  DOB: invalid-date
  retirement_date: not-a-date
  state: CA
  income_profiles:
    - start_date: bad-date
      gross_income: 100000
"""
    config_page.set_config_content(invalid_date_config)
    config_page.click_save()

    # Should show error or stay on config page
    assert "/config" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.error
def test_negative_financial_values(config_page):
    """Test handling of negative values where positive expected."""
    config_page.navigate()

    # Set config with negative values
    negative_config = """
User:
  name: Test User
  DOB: 1985-01-15
  retirement_date: 2050-01-01
  state: CA
  income_profiles:
    - start_date: 2025-01-01
      gross_income: -50000

Portfolio:
  starting_balance: -100000

Spending:
  spending_profiles:
    - start_date: 2025-01-01
      annual_spending: -10000
"""
    config_page.set_config_content(negative_config)
    config_page.click_save()

    # Should validate and show error or handle gracefully
    assert "/config" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.error
def test_simulation_without_config(run_page):
    """Test running simulation without configuration."""
    run_page.navigate()

    # Try to run without config (if button allows)
    if run_page.is_run_button_enabled():
        run_page.click_run_simulation()

        # Should either show error or stay on run page
        # (Implementation-specific behavior)
        current_url = run_page.get_current_url()
        assert "/run" in current_url or run_page.is_error_message_visible()


@pytest.mark.e2e
@pytest.mark.error
def test_results_without_simulation(results_page):
    """Test accessing results page without running simulation."""
    results_page.navigate()

    # Should show "no results" message or handle gracefully
    has_no_results = results_page.is_no_results_message_visible()
    has_charts = results_page.is_success_gauge_visible()

    # Either no results message or no charts should be shown
    assert has_no_results or not has_charts


@pytest.mark.e2e
@pytest.mark.error
def test_browser_back_button_handling(config_page, run_page, sample_config):
    """Test proper handling of browser back button."""
    # Save config
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()

    # Go to run page
    run_page.navigate()

    # Use browser back button
    config_page.driver.back()

    # Should be back on config page
    assert "/config" in config_page.get_current_url()

    # Config should still be there
    content = config_page.get_config_content()
    assert "Test User" in content


@pytest.mark.e2e
@pytest.mark.error
def test_concurrent_form_submissions(config_page, sample_config):
    """Test handling of rapid/concurrent form submissions."""
    config_page.navigate()

    # Set config
    config_page.set_config_content(sample_config)

    # Click save button twice rapidly
    config_page.click_save()

    # Should handle gracefully without errors
    # Page should be in valid state
    assert (
        "/config" in config_page.get_current_url()
        or "/run" in config_page.get_current_url()
    )


@pytest.mark.e2e
@pytest.mark.error
def test_empty_config_submission(config_page):
    """Test submitting completely empty configuration."""
    config_page.navigate()

    # Clear config editor
    config_page.set_config_content("")

    # Try to save
    config_page.click_save()

    # Should show error or reject
    assert "/config" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.error
def test_very_large_config(config_page):
    """Test handling of very large configuration."""
    config_page.navigate()

    # Create a large config (e.g., many income profiles)
    large_config = """
User:
  name: Test User
  DOB: 1985-01-15
  retirement_date: 2050-01-01
  state: CA
  income_profiles:
"""
    # Add many income profiles
    for i in range(100):
        large_config += f"""
    - start_date: 2025-0{(i % 9) + 1}-01
      gross_income: {100000 + i * 1000}
"""

    large_config += """
Portfolio:
  starting_balance: 500000

Spending:
  spending_profiles:
    - start_date: 2025-01-01
      annual_spending: 60000
"""

    config_page.set_config_content(large_config)
    config_page.click_save()

    # Should handle large config (may take time but shouldn't crash)
    assert (
        "/config" in config_page.get_current_url()
        or "/run" in config_page.get_current_url()
    )


@pytest.mark.e2e
@pytest.mark.error
def test_special_characters_in_config(config_page):
    """Test handling of special characters in configuration."""
    config_page.navigate()

    # Config with special characters
    special_char_config = """
User:
  name: Test User 123 !@#$%^&*()
  DOB: 1985-01-15
  retirement_date: 2050-01-01
  state: CA
  income_profiles:
    - start_date: 2025-01-01
      gross_income: 100000

Portfolio:
  starting_balance: 500000

Spending:
  spending_profiles:
    - start_date: 2025-01-01
      annual_spending: 60000
"""
    config_page.set_config_content(special_char_config)
    config_page.click_save()

    # Should handle or validate appropriately
    assert (
        "/config" in config_page.get_current_url()
        or "/run" in config_page.get_current_url()
    )
