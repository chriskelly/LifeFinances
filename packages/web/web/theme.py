from __future__ import annotations

# Seeded from Pico CSS 2.1.1 default light:
# https://picocss.com/docs/css-variables
PICO_STYLESHEET_HREF = (
    "https://cdn.jsdelivr.net/npm/@picocss/pico@2.1.1/css/pico.fluid.classless.min.css"
)

BACKGROUND = "#fff"
COLOR = "#373c44"
MUTED = "#646b79"
MUTED_BORDER = "rgb(231, 234, 239.5)"

PRIMARY = "#0172ad"
PRIMARY_BACKGROUND = "#0172ad"
PRIMARY_HOVER = "#015887"
PRIMARY_HOVER_BACKGROUND = "#02659a"
PRIMARY_UNDERLINE = "rgba(1, 114, 173, 0.5)"
PRIMARY_FOCUS = "rgba(2, 154, 232, 0.5)"
PRIMARY_INVERSE = "#fff"

# del / invalid from Pico light; banner fill is ours (Pico has no alert-bg token)
DANGER_TEXT = "rgb(136, 56.5, 53)"
DANGER_BORDER = "rgb(183.5, 105.5, 106.5)"
DANGER_BACKGROUND = "rgb(253, 236, 234)"

# Density — Pico defaults are roomy for a dense planner UI.
# Pico fluid also grows --pico-font-size at large breakpoints; we re-set it here
# (this <style> loads after Pico) so the size stays pinned.
# Adjust these constants to retune; more compact examples in AGENTS.md.
FONT_SIZE = "87.5%"  # Pico default 100% (+ larger at wide breakpoints)
LINE_HEIGHT = "1.4"  # Pico default 1.5
SPACING = "0.875rem"  # Pico default 1rem
FORM_SPACING_VERTICAL = "0.35rem"  # Pico default 0.75rem
FORM_SPACING_HORIZONTAL = "0.65rem"  # Pico default 1rem

CHART_BAND_FILL = "rgba(1, 114, 173, 0.2)"
CHART_SERIES: tuple[str, ...] = (
    PRIMARY,
    PRIMARY_HOVER,
    COLOR,
    MUTED,
    PRIMARY_HOVER_BACKGROUND,
)

PICO_LIGHT: dict[str, str] = {
    "--pico-font-size": FONT_SIZE,
    "--pico-line-height": LINE_HEIGHT,
    "--pico-spacing": SPACING,
    "--pico-form-element-spacing-vertical": FORM_SPACING_VERTICAL,
    "--pico-form-element-spacing-horizontal": FORM_SPACING_HORIZONTAL,
    "--pico-background-color": BACKGROUND,
    "--pico-color": COLOR,
    "--pico-muted-color": MUTED,
    "--pico-muted-border-color": MUTED_BORDER,
    "--pico-primary": PRIMARY,
    "--pico-primary-background": PRIMARY_BACKGROUND,
    "--pico-primary-border": PRIMARY_BACKGROUND,
    "--pico-primary-underline": PRIMARY_UNDERLINE,
    "--pico-primary-hover": PRIMARY_HOVER,
    "--pico-primary-hover-background": PRIMARY_HOVER_BACKGROUND,
    "--pico-primary-hover-border": PRIMARY_HOVER_BACKGROUND,
    "--pico-primary-hover-underline": PRIMARY_HOVER,
    "--pico-primary-focus": PRIMARY_FOCUS,
    "--pico-primary-inverse": PRIMARY_INVERSE,
    "--pico-form-element-invalid-border-color": DANGER_BORDER,
    "--pico-form-element-invalid-active-border-color": DANGER_TEXT,
    "--pico-form-element-invalid-focus-color": DANGER_TEXT,
    "--pico-del-color": DANGER_TEXT,
}


def pico_root_css() -> str:
    assignments = "\n".join(f"  {name}: {value};" for name, value in PICO_LIGHT.items())
    return (
        ':root,\n[data-theme="light"] {\n'
        f"{assignments}\n"
        "}\n"
        ".form-error,\n.results-error,\n.error-message {\n"
        f"  color: {DANGER_TEXT};\n"
        f"  background: {DANGER_BACKGROUND};\n"
        f"  border-color: {DANGER_BORDER};\n"
        "}\n"
    )
