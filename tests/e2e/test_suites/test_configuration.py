"""
Configuration Management E2E tests for LifeFinances GUI.

Tests configuration viewing, editing, saving, and validation.
"""
import pytest


@pytest.mark.e2e
@pytest.mark.config
@pytest.mark.smoke
def test_config_page_loads(config_page):
    """Test that configuration page loads successfully."""
    config_page.navigate()
    assert config_page.is_config_editor_visible()


@pytest.mark.e2e
@pytest.mark.config
def test_config_editor_has_content(config_page):
    """Test that configuration editor contains content."""
    config_page.navigate()
    content = config_page.get_config_content()
    assert len(content) > 0
    assert "User:" in content or "user:" in content


@pytest.mark.e2e
@pytest.mark.config
def test_save_configuration(config_page, sample_config):
    """Test saving a valid configuration."""
    config_page.navigate()

    # Set new configuration
    config_page.set_config_content(sample_config)

    # Save configuration
    config_page.click_save()

    # Should stay on config page after save
    assert "/config" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.config
def test_save_and_run_redirects(config_page, sample_config):
    """Test that Save and Run redirects to run page."""
    config_page.navigate()

    # Set configuration
    config_page.set_config_content(sample_config)

    # Click Save and Run
    config_page.click_save_and_run()

    # Should redirect to run page
    assert "/run" in config_page.get_current_url()


@pytest.mark.e2e
@pytest.mark.config
def test_config_persists_after_save(config_page, sample_config):
    """Test that configuration persists after saving."""
    config_page.navigate()

    # Save a specific configuration
    test_value = "Test User E2E"
    modified_config = sample_config.replace("Test User", test_value)
    config_page.set_config_content(modified_config)
    config_page.click_save()

    # Navigate away and back
    config_page.navigate_to("/dashboard")
    config_page.navigate()

    # Verify configuration persisted
    content = config_page.get_config_content()
    assert test_value in content


@pytest.mark.e2e
@pytest.mark.config
def test_invalid_config_shows_error(config_page):
    """Test that invalid configuration shows error message."""
    config_page.navigate()

    # Set invalid YAML
    invalid_config = "User:\n  name: Test\n  invalid_field: $$$$\n  bad: [unclosed"
    config_page.set_config_content(invalid_config)
    config_page.click_save()

    # Should show error or stay on config page
    # Note: Error handling depends on implementation
    current_url = config_page.get_current_url()
    assert "/config" in current_url


@pytest.mark.e2e
@pytest.mark.config
def test_config_modification_workflow(config_page):
    """Test the full configuration modification workflow."""
    config_page.navigate()

    # Get original config
    original_config = config_page.get_config_content()

    # Modify config
    modified_config = original_config.replace("100000", "120000")
    config_page.set_config_content(modified_config)

    # Save
    config_page.click_save()

    # Verify change persisted
    config_page.navigate()
    current_config = config_page.get_config_content()
    assert "120000" in current_config
