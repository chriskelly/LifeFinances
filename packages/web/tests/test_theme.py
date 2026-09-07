from web import theme


def test_pico_root_css_targets_forced_light_root():
    css = theme.pico_root_css()

    assert css.startswith(':root,\n[data-theme="light"] {')


def test_pico_root_css_assigns_palette_background_and_primary():
    css = theme.pico_root_css()

    assert f"--pico-background-color: {theme.BACKGROUND};" in css
    assert f"--pico-primary: {theme.PRIMARY};" in css


def test_pico_root_css_omits_secondary_and_contrast_roles():
    """v1 live set is surfaces + primary family + invalid/danger — pinned."""
    css = theme.pico_root_css()

    assert "--pico-secondary:" not in css
    assert "--pico-contrast:" not in css


def test_pico_root_css_styles_error_banners_from_danger_constants():
    css = theme.pico_root_css()

    assert f"color: {theme.DANGER_TEXT};" in css
    assert f"background: {theme.DANGER_BACKGROUND};" in css
    assert f"border-color: {theme.DANGER_BORDER};" in css


def test_pico_root_css_emits_density_tokens_from_constants():
    css = theme.pico_root_css()

    assert f"--pico-font-size: {theme.FONT_SIZE};" in css
    assert f"--pico-line-height: {theme.LINE_HEIGHT};" in css
    assert f"--pico-spacing: {theme.SPACING};" in css
    assert (
        f"--pico-form-element-spacing-vertical: {theme.FORM_SPACING_VERTICAL};" in css
    )
    assert (
        f"--pico-form-element-spacing-horizontal: {theme.FORM_SPACING_HORIZONTAL};"
        in css
    )
