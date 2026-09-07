# Web UI theme and visual polish — design

**Issue:** [#198](https://github.com/chriskelly/LifeFInances/issues/198)  
**Status:** Open design (delete this file when the feature lands on `main`)  
**Scope:** `packages/web` only

## Summary

Polish the FastAPI + Jinja2 + HTMX UI with Pico.css as a classless baseline, a thin custom CSS layer for the split-pane shell, and semantic color tokens owned by a single Python module shared with Plotly. Ship one polished light theme. No theme switcher, no Node bundler, no React rewrite.

## Goals

1. General visual polish — typography, spacing, forms, header, chart panel — so the app feels intentional rather than scaffolded.
2. Adopt a lightweight UI approach that fits server-rendered HTML + HTMX (prefer no JS bundler).
3. Express the color palette as CSS custom properties, with chart colors wired from the same source of truth.

## Non-goals

- Dark mode or user-facing theme / accent switcher (tokens must make a later dark theme easy).
- Rewriting the UI as a React/SPA frontend.
- Pixel-perfect brand identity before core editor completeness.
- Changing simulation or chart *data* semantics (presentation only).
- Exhaustive visual audit of every editor section.
- Screenshot / visual-regression test suite.

## Decision record: UI approach comparison

Constraints: Jinja partials, HTMX swaps, Plotly CDN, no Node build preferred, owner relies on agents for CSS.

| Approach | Fit | Ongoing cost | Agent risk |
| -------- | --- | ------------ | ---------- |
| **Pico.css + thin custom layer** | Strong — classless forms/type, CDN or one vendored file | Small `style.css` for shell only | Low if overrides are forbidden by policy; failure mode is override pile-up |
| Custom CSS variables only (hand-rolled / Open Props primitives) | Fine — full control | Larger CSS surface to invent and maintain | Higher — agents re-invent spacing/forms each session |
| Heavier toolkit (Bootstrap / Bulma / DaisyUI) | Weak — class churn, heavier than needed | High template coupling | High — large class vocabulary, fights partials |

**Recommendation (adopted):** Pico.css + thin custom layer.

**Aesthetic target:** Quiet soft product — Pico’s calm defaults with lightly tightened density for the planner editor (between utilitarian and soft product UI).

## Architecture

```
theme.py  ──►  :root CSS vars (injected in base.html)
     │
     └──►  charts.py (layout chrome + series / band colors)

Pico.css (pinned)  +  style.css (shell / HTMX / Plotly height only)
```

1. **Pico.css** — pinned CDN by default (exact version URL); vendor under `web/static/` only if offline/reproducibility becomes a real need. Loaded before `style.css`. Use Pico’s classless element styles; do not adopt Pico’s optional class-heavy patterns unless a specific control needs them.
2. **`web/theme.py`** — single source of truth for semantic colors.
3. **Jinja** injects `:root { --color-… }` from `theme.py` in `base.html`.
4. **`style.css`** — split pane, header/plan menu, Plotly `min-height`, form-error banner; uses `var(--color-…)`; no scattered hex.
5. **`charts.py`** — imports theme constants; no client-side `getComputedStyle` chart restyling.

HTMX and Plotly load/settle behavior stay as documented in `packages/web/AGENTS.md` (`htmx:afterSettle` → `Plotly.react`; keep `#results-chart` min-height).

## Components

### `web/theme.py`

Semantic constants only, for example:

- Surfaces / text: bg, fg, surface, border, muted
- Feedback: accent, danger (and matching soft backgrounds if needed for alerts)
- Charts: band fill, ordered series palette for percentile lines and wealth layers
- Helper that emits the `:root` custom-property block (or a dict templates iterate)

No runtime theme switching in this issue.

### Templates

- Keep structural / behavioral classes the shell and JS need: `layout`, `editor-pane`, `app-header`, `plan-menu*`, boundary/list-row hooks, checkbox partners, Plotly/results ids.
- Drop or simplify presentational classes where Pico’s element styles suffice.
- **Baseline polish acceptance surface:** app shell (header + panes), **Household** editor section, results chart panel. Other sections inherit Pico + shared section chrome; fix only if something obviously breaks.

### `base.html`

- Pico stylesheet (pinned version) before `style.css`.
- Injected theme `:root` block.
- Existing HTMX + Plotly CDNs unchanged in role.

### `style.css`

- Rewrite around CSS variables from the injected theme.
- Retain split-pane grid, overflow scrolling, plan-menu positioning, `#results-chart` min-height, error banner.
- Remove redundant element styles Pico already provides; do not grow into a second design system.

### `charts.py`

- Replace hardcoded band fill (and default series reliance) with `theme` imports.
- Apply layout paper / font / grid colors from the same module.
- Explicit series colors for percentile and wealth-composition traces where practical.

## Plotly theming choice

| Option | Final-code complexity | Decision |
| ------ | --------------------- | -------- |
| A — layout chrome only; Plotly default series colors | Low | Rejected — easy drift, weaker token story |
| **B — shared palette; one server-side source of truth** | Low–moderate | **Adopted** |
| C — browser reads CSS vars and restyles after swap | High (dual ownership, HTMX fragility) | Rejected |

## Agent / maintenance policy

Promote into `packages/web/AGENTS.md` when implementing:

- Prefer Pico defaults; custom CSS only for layout/shell/Plotly/HTMX concerns.
- Do not accumulate Pico overrides; if Pico fights a layout, prefer a minimal structural tweak over broad restyling.
- All semantic colors live in `theme.py`; templates and charts must not invent parallel hex values.

## Testing

- Contract: chart band fill (and other wired chart colors) equal `theme` constants — import the constant in the test; do not duplicate literals.
- Lightweight home/smoke: response includes Pico link and `--color-` / `:root` injection.
- Existing chart behavior tests remain; update fill assertions to use theme constants.
- No visual regression / screenshot suite.

## Documentation deliverables

- This design spec (comparison write-up + adopted recommendation) — satisfies the issue’s short write-up acceptance item.
- Durable rules in `packages/web/AGENTS.md` as above.
- Delete this spec when the feature is done (repo docs policy).

## Acceptance criteria (from #198, refined)

- [ ] Comparison of 2–3 UI approaches recorded (this doc).
- [ ] Recommendation adopted: Pico + thin custom layer.
- [ ] Color palette as CSS custom properties; chart colors from `theme.py`.
- [ ] Baseline visual pass: shell + Household + results charts (light theme only).

## Implementation notes (for the follow-on plan)

- Pin Pico via exact CDN version URL; record the pin in `packages/web/AGENTS.md`.
- Jinja global or context processor for theme CSS emission — pick the smallest hook that `base.html` can call once.
- Keep `editor_conditional.js` / `editor_lists.js` class hooks intact when stripping presentational classes.
