# Web UI theme and visual polish — design

**Issue:** [#198](https://github.com/chriskelly/LifeFInances/issues/198)  
**Status:** Open design (delete this file when the feature lands on `main`)  
**Scope:** `packages/web` only

## Summary

Polish the FastAPI + Jinja2 + HTMX UI with Pico.css as a classless baseline, a thin custom CSS layer for the split-pane shell, and a single Python palette module (`theme.py`) that feeds both Pico (`--pico-*` overrides) and Plotly. Force light theme for v1. No theme switcher, no Node bundler, no React rewrite.

## Goals

1. General visual polish — typography, spacing, forms, header, chart panel — so the app feels intentional rather than scaffolded.
2. Adopt a lightweight UI approach that fits server-rendered HTML + HTMX (prefer no JS bundler).
3. One editable palette in `theme.py` that flows to UI chrome and charts.

## Non-goals

- Dark mode / `prefers-color-scheme` theming in this issue (Pico can do it; Plotly cannot follow cleanly without a client palette bridge — deferred).
- User-facing theme or accent switcher.
- Parallel semantic `--color-*` token system beside Pico.
- Rewriting the UI as a React/SPA frontend.
- Pixel-perfect brand identity; inventing a custom color story beyond Pico’s defaults.
- Changing simulation or chart *data* semantics (presentation only).
- Exhaustive visual audit of every editor section.
- Screenshot / visual-regression test suite.

## Decision record: UI approach comparison

Constraints: Jinja partials, HTMX swaps, Plotly CDN, no Node build preferred, owner relies on agents for CSS.

| Approach | Fit | Ongoing cost | Agent risk |
| -------- | --- | ------------ | ---------- |
| **Pico.css + thin custom layer** | Strong — classless forms/type, CDN | Small `style.css` for shell only | Low if overrides are forbidden by policy; failure mode is override pile-up |
| Custom CSS variables only (hand-rolled / Open Props primitives) | Fine — full control | Larger CSS surface to invent and maintain | Higher — agents re-invent spacing/forms each session |
| Heavier toolkit (Bootstrap / Bulma / DaisyUI) | Weak — class churn, heavier than needed | High template coupling | High — large class vocabulary, fights partials |

**Recommendation (adopted):** Pico.css + thin custom layer (better for agentic CSS maintenance than a fully custom token sheet).

**Aesthetic target:** Quiet soft product — start from **stock Pico light** (seeded into `theme.py`); retint later by editing palette constants. Not attached to preserving today’s hand-rolled look.

## Architecture

```
theme.py  ──►  --pico-* overrides (+ danger) injected in base.html
     │
     └──►  charts.py (layout chrome + series / band colors)

Pico.css (pinned CDN)  +  style.css (shell / HTMX / Plotly height only)
<html data-theme="light">
```

1. **Pico.css** — pinned CDN (exact version URL); load before `style.css`. Prefer classless element styles; do not adopt Pico’s optional class-heavy patterns unless a specific control needs them. Vendor under `web/static/` only if offline/reproducibility becomes a real need.
2. **`web/theme.py`** — single source of truth. Emits Pico variable overrides (not a parallel `--color-*` vocabulary). Same module holds chart constants.
3. **`base.html`** — `data-theme="light"` on `<html>` so OS dark mode does not half-theme the UI while charts stay light; inject `theme.pico_root_css()` (or equivalent) once.
4. **`style.css`** — shell only: split pane, header/plan menu positioning, Plotly `min-height`, error banner layout. Uses `var(--pico-…)` (and danger vars from theme). **No hex literals.**
5. **`charts.py`** — imports theme constants; no client-side `getComputedStyle` chart restyling.

HTMX and Plotly load/settle behavior stay as documented in `packages/web/AGENTS.md` (`htmx:afterSettle` → `Plotly.react`; keep `#results-chart` min-height).

### Why force light (grilling)

Pico can auto-dark via `prefers-color-scheme`. Plotly figures are server-baked JSON and do not see CSS variables. Without a small client dual-palette bridge, dark UI + light charts diverge. **v1 forces light** so UI and charts stay aligned. Dark is a follow-up (emit dark `--pico-*` + dark chart palette; tiny JS on `afterSettle` picks palette).

### Why `--pico-*` not `--color-*` (grilling)

Pico already consumes `--pico-primary`, `--pico-background-color`, etc. A parallel `--color-*` set plus a bridge is two vocabularies and high agent drift. Coupling to Pico’s names is an accepted tradeoff for maintainability.

## Components

### `web/theme.py`

**Editable palette** at the top (seeded by copying Pico’s default light values for the live set). Day-to-day retinting happens here only.

**Live emitted set (v1):**

- Surfaces: background, color (fg), muted (and card/border Pico vars if the shell needs them)
- Primary family (Pico’s documented override set): `--pico-primary`, `--pico-primary-background`, underline, hover, hover-background, focus, inverse (and border companions if required for buttons/links to retint correctly)
- Danger: text + soft background + border for `.form-error` / alerts; map into Pico invalid form vars where practical (`--pico-form-element-invalid-*`, etc.)
- Charts: band fill, ordered series palette, layout paper/font/grid colors derived from the same surfaces/primary

**Not emitted in v1:** secondary / contrast Pico roles. Document how to add them in `packages/web/AGENTS.md` (link Pico CSS variables docs; move entries into the live map — do not invent parallel tokens). Do **not** maintain a large commented-out copy of Pico’s full theme (goes stale).

Helper: `pico_root_css()` (or dict → Jinja) emits:

```css
:root,
[data-theme="light"] {
  --pico-background-color: …;
  --pico-primary: …;
  /* …live set only… */
}
```

### Templates

- Keep structural / behavioral classes the shell and JS need: `layout`, `editor-pane`, `app-header`, `plan-menu*`, boundary/list-row hooks, checkbox/partner toggles, Plotly/results ids.
- Prefer stock Pico styling for forms and section chrome; drop redundant presentational CSS/classes when Pico covers them.
- **Baseline polish surface:** app shell (header + panes), **Household** editor section, results chart panel. Other sections inherit; fix only if obviously broken.

### Pico vs compact controls (grilling)

1. **Try stock Pico first** (owner is not attached to current compact UI).
2. If plan-menu × delete or boundary rows are unusable, allow **one named escape hatch** in `style.css` (e.g. `.compact-controls`) that only adjusts spacing/sizing and still uses `--pico-*` for color — no ad-hoc per-widget override pile-up.
3. Prefer a structural HTML tweak before adding the hatch; never open-ended “agent judgment” overrides.

### `charts.py`

- Replace hardcoded band fill (and default series reliance) with `theme` imports.
- Apply layout paper / font / grid from theme.
- Explicit series colors for percentile and wealth-composition traces where practical.

## Plotly theming choice

| Option | Final-code complexity | Decision |
| ------ | --------------------- | -------- |
| A — layout chrome only; Plotly default series colors | Low | Rejected — weaker single-palette story |
| **B — shared palette; one server-side source of truth** | Low–moderate | **Adopted** (`theme.py` → charts + `--pico-*`) |
| C — browser reads CSS vars and restyles after swap | High | Rejected for v1; may revisit as part of dark-mode follow-up |

## Agent / maintenance policy

Promote into `packages/web/AGENTS.md` when implementing:

- Prefer Pico defaults; custom CSS only for layout/shell/Plotly/HTMX/`min-height`/error banner layout.
- To retint UI + charts, edit the live palette in `theme.py` only.
- To add secondary/contrast (or other Pico roles), copy from [Pico CSS variables](https://picocss.com/docs/css-variables) into the live emitted map — do not invent parallel `--color-*`.
- Do not accumulate Pico overrides; try stock Pico, then structural HTML, then the single `.compact-controls` (or equivalent) hatch.
- No hex in templates or `style.css`.

## Testing

- Contract: chart band fill (and other wired chart colors) equal `theme` constants — import the constant; do not duplicate literals.
- Lightweight home/smoke: Pico stylesheet link, `data-theme="light"`, and injected `--pico-` overrides present.
- Existing chart behavior tests remain; update fill assertions to use theme constants.
- No visual regression / screenshot suite.

## Definition of done (visual pass)

**Mechanical checklist (agents):**

- [ ] Pico pinned CDN linked; `data-theme="light"` on root
- [ ] `theme.py` seeds Pico default light for live set; emits `--pico-*`; charts import same module
- [ ] Danger tokens drive error banners (no hex left in `style.css`)
- [ ] Split-pane scroll + `#results-chart` min-height still correct
- [ ] Household form usable under Pico; compact hatch only if necessary
- [ ] Tests: theme↔chart contract + home smoke for Pico / `data-theme` / `--pico-`
- [ ] `packages/web/AGENTS.md` updated with policy above

**Human sign-off:** owner eyeballs the running app once (shell + Household + charts).

## Documentation deliverables

- This design spec (comparison + adopted recommendation) — satisfies the issue’s short write-up acceptance item.
- Durable rules in `packages/web/AGENTS.md` as above.
- Delete this spec when the feature is done (repo docs policy).

## Acceptance criteria (from #198, refined)

- [ ] Comparison of 2–3 UI approaches recorded (this doc).
- [ ] Recommendation adopted: Pico + thin custom layer; `theme.py` → `--pico-*` + charts.
- [ ] Color palette editable in one place; CSS custom properties are Pico’s; chart colors from `theme.py`.
- [ ] Baseline visual pass: shell + Household + results charts (forced light); mechanical checklist + owner eyeball.

## Implementation notes (for the follow-on plan)

- Pin Pico via exact CDN version URL; record the pin in `packages/web/AGENTS.md`.
- Seed live palette constants from the pinned Pico version’s default light theme (primary family, surfaces, invalid/danger-related vars).
- Jinja global or smallest hook so `base.html` can call `pico_root_css()` once.
- Keep `editor_conditional.js` / `editor_lists.js` class hooks intact when stripping presentational classes.
- Illustrative shape (not final API): palette constants → `PICO_LIGHT` dict → `pico_root_css()`; `charts.py` imports `CHART_BAND_FILL` / `CHART_SERIES` / surface colors from the same module.
