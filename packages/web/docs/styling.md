# Web styling and palette

Scope: theme tokens, Pico.css usage, and CSS boundaries. Read before changing
colors, density, or `../web/static/style.css`.

- Pico.css **2.1.1** fluid classless, pinned in `web.theme.PICO_STYLESHEET_HREF`. Load Pico, then `theme.pico_root_css()`, then `../web/static/style.css`.
- `<html data-theme="light">` is required in v1 so OS dark mode cannot restyle the shell while Plotly stays on its default light look.
- **Retint UI** by editing constants in `../web/theme.py` only. Do not add `--color-*` tokens. Do not put hex in templates or `../web/static/style.css`. `../web/static/favicon.svg` is the one static colour carrier because a browser icon cannot read `../web/theme.py`; `../tests/test_app.py` pins its primary fill to `theme.PRIMARY`.
- **Charts** use stock Plotly series colors. The percentile band fill (`BAND_FILLCOLOR` in `../web/charts.py`) is the only explicit chart color we set; do not wire chart colors through `../web/theme.py`.
- **Density** (overall size): edit `FONT_SIZE`, `LINE_HEIGHT`, `SPACING`, `FORM_SPACING_VERTICAL`, and `FORM_SPACING_HORIZONTAL` in `../web/theme.py`. Shell gaps in `../web/static/style.css` (layout/`editor-pane` padding) are separate if the page still feels roomy.
- Live emitted Pico roles: surfaces, primary family, invalid/del, plus density tokens above. To add secondary/contrast, copy names from https://picocss.com/docs/css-variables into `PICO_LIGHT` — do not comment-dump Pico's full theme.
- Custom CSS is for split-pane shell, plan-menu positioning, Plotly `#results-chart` min-height, HTMX error-banner layout, and JS-driven show/hide. Prefer stock Pico for forms.
- If Pico makes plan-menu × or boundary rows unusable: try a structural HTML tweak first; then **one** named hatch (`.compact-controls`) that only changes spacing and still uses `--pico-*` for color. No ad-hoc per-widget override pile-up.
