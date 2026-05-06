# Frontend Agent Guide (React + TypeScript)

This file applies to everything under `frontend/`. Read [/AGENTS.md](../AGENTS.md) first for repo-wide policy.

## Stack

- React 19, TypeScript 5.9 (strict)
- Vite 7 (dev/build), Vitest 4 + jsdom (tests), ESLint 9 + typescript-eslint
- React Testing Library 16, `@testing-library/user-event` 14, `@testing-library/jest-dom`
- MSW 2 for HTTP mocking at the network boundary
- Node engines: `^20.19.0 || ^22.12.0 || >=24.0.0` (pinned in [package.json](package.json) and [.nvmrc](../.nvmrc))

## Commands

Run from `frontend/` (or via `make` from the repo root).

| Action                      | Command                |
| --------------------------- | ---------------------- |
| Dev server (port 5173)      | `npm run dev`          |
| Tests, watch mode           | `npm run test`         |
| Tests, single CI-style run  | `npm run test:run`     |
| Tests UI                    | `npm run test:ui`      |
| Lint                        | `npm run lint`         |
| Typecheck + production build | `npm run build`        |

The cross-stack `make test` from the repo root runs `npm run test:run` after pytest. `make lint` does NOT currently run `npm run lint` — run it explicitly when you change frontend code.

After substantive frontend edits you MUST run `npm run test:run` and `npm run lint` and confirm both pass.

## Frontend layout

```
frontend/
├── package.json, vite.config.ts, vitest.config.ts, eslint.config.js
├── index.html
└── src/
    ├── main.tsx, App.tsx, App.css, index.css
    ├── App.test.tsx              # colocated tests beside source
    ├── services/
    │   └── api.ts                # SINGLE typed boundary to the backend
    ├── types/
    │   └── api.ts                # API contract types mirroring backend models
    ├── test/
    │   └── setup.ts              # global test setup (jest-dom, MSW, etc.)
    └── assets/
```

Tests are colocated as `*.test.tsx` next to the source they protect. Don't introduce a parallel `__tests__/` tree without justification — the convention here is colocation.

## Architecture — Do / Don't

### Composition over monoliths

Split data fetching, state orchestration, and presentation into separate components or hooks. If a component file is approaching ~200 lines and combines all three, refactor *as part of* whatever change you're making.

### Keep state local; separate the kinds

State falls into three categories that should NOT be merged:

- **Server state** — what the backend returned. Owned by the data-fetching layer (e.g. a hook around `services/api.ts`).
- **Derived UI state** — computed from server state or props. Memoize in the consuming component.
- **Transient interaction state** — input values, hover, "is this dialog open." Lives in the leaf component.

Don't introduce a global store (Context, Redux, etc.) until prop composition is genuinely insufficient. Lifting state to the nearest common ancestor is almost always the right answer first.

### Typed API boundary in one place

All HTTP traffic to the backend goes through [src/services/api.ts](src/services/api.ts). Response shapes live in [src/types/api.ts](src/types/api.ts) and MUST mirror the backend's Pydantic / OpenAPI contracts.

Do:

```ts
import { fetchConfig } from './services/api'
const cfg = await fetchConfig()
```

Don't:

```tsx
const res = await fetch('/api/config')
const data = await res.json()
```

If you need a new endpoint, add it to `services/api.ts` AND a matching type in `types/api.ts` in the same change.

### Feature-oriented organization

Group hooks, components, and feature-local helpers near the feature they support. Reusable UI primitives go somewhere shared (e.g. `src/components/` if/when you add it); feature-specific components stay with their feature.

### Required UI states for any data view

Every component that fetches or derives data MUST render explicit states for:

1. **Loading** (skeleton, spinner, or status message)
2. **Success** (the actual content)
3. **Empty** (no data → useful prompt, not a blank screen)
4. **Error** (something failed → human-readable message + retry where possible)

A spinner alone is NOT enough. Empty and error must be visually distinguishable.

### Accessibility is non-negotiable

- Use semantic HTML (`<button>`, `<form>`, `<label>`, `<table>`, headings) before reaching for ARIA.
- Every interactive element MUST be keyboard-operable and have a visible focus state.
- Every form input MUST have an explicit `<label>` (or `aria-label`/`aria-labelledby`). Placeholder text is NEVER the only label.
- Status messages live in regions with appropriate `role="status"` / `role="alert"` so assistive tech announces them.
- Accessibility regressions in primary user flows are bugs, not polish.

### Named option objects, not long positional arg lists

Do:

```ts
function runSimulation(opts: { trials: number; seed?: number }): Promise<Result>
```

Don't:

```ts
function runSimulation(trials: number, seed: number, dryRun: boolean): Promise<Result>
```

### Style consistency

Reuse shared UI patterns (buttons, inputs, spacing, typography, validation display, status messaging) through common components or documented conventions. Don't reimplement them ad hoc per feature.

## Testing — TDD with React Testing Library + MSW

Frontend tests express **user-observable behavior**, not implementation details. Read these rules in full before writing or reviewing any test.

### The cycle

1. Write a failing test that names a user-observable outcome.
2. Implement the minimum component / hook code to make it pass.
3. Refactor; the test stays green.

### Tooling — what to use, what NOT to use

- **Test runner**: Vitest. Tests run in jsdom (`vitest.config.ts`).
- **Component / integration tests**: React Testing Library. NEVER reach into component internals (state, refs, private methods).
- **User gestures**: `@testing-library/user-event`. NOT `fireEvent`, except where user-event genuinely cannot model the case (and call that out in a comment).
- **HTTP mocking**: MSW at the network boundary (`http.get`, `http.put`, `setupServer`). NEVER spy on or replace `fetch` inside the component under test.
- **Hooks**: test with `renderHook` from `@testing-library/react`, wrapped in explicit providers that match production composition.

### Querying — accessibility-first, always

Use queries in this order of preference:

1. `getByRole(name)` — role + accessible name
2. `getByLabelText` (forms), `getByText` (visible text)
3. `getByAltText`, `getByTitle`
4. `getByTestId` — only when no user-equivalent query is practical, AND with a comment explaining why

Do:

```ts
const save = screen.getByRole('button', { name: /save/i })
const yaml = screen.getByRole('textbox', { name: /configuration \(yaml\)/i })
```

Don't:

```ts
const save = container.querySelector('.btn-save')
const yaml = screen.getByTestId('yaml-textarea')   // only with justification
```

### Async — `findBy*`, `waitFor`, async user-event

Async UI MUST be asserted with `findBy*`, `waitFor`, or `await user.click(...)`-style APIs.

Do:

```ts
expect(await screen.findByText(/configuration loaded/i)).toBeInTheDocument()
await waitFor(() => expect(textarea).toHaveValue(sampleYaml))
```

Don't:

```ts
await new Promise((r) => setTimeout(r, 200))   // arbitrary wait — flake source
expect(screen.getByText(/loaded/i)).toBeInTheDocument()
```

### Network handler purity — assertions go in the test, not the handler

MSW handlers shape responses. They MUST NOT contain `expect(...)`. An `expect` thrown inside a handler surfaces to the component as an opaque network error and obscures the real failure.

Do:

```ts
let captured: { content: string } | undefined
server.use(
  http.put(CONFIG_URL, async ({ request }) => {
    captured = (await request.json()) as { content: string }
    return HttpResponse.json({ ok: true })
  }),
)
await user.click(screen.getByRole('button', { name: /save/i }))
await waitFor(() => expect(captured?.content).toContain('age: 31'))
```

Don't:

```ts
server.use(
  http.put(CONFIG_URL, async ({ request }) => {
    const body = await request.json()
    expect(body.content).toContain('age: 31')   // ❌ throws as network error
    return HttpResponse.json({ ok: true })
  }),
)
```

### Determinism — no wall-clock waits

In-flight UI states (disabled controls, spinners, loading skeletons) MUST be exercised with **deferred promises the test resolves explicitly**, or with fake timers. Arbitrary `setTimeout` delays in handlers or test bodies — used to "wait long enough" for an assertion to land — MUST NOT be used.

Do:

```ts
let resolveRun!: (v: { success_percentage: number }) => void
server.use(
  http.post(RUN_URL, () =>
    new Promise<HttpResponse>((res) => {
      resolveRun = (data) => res(HttpResponse.json(data))
    }),
  ),
)
await user.click(screen.getByRole('button', { name: /run simulation/i }))
expect(screen.getByRole('button', { name: /run simulation/i })).toBeDisabled()
resolveRun({ success_percentage: 0.9 })
await screen.findByText(/90/)
```

### Negative presence — `queryBy*().not.toBeInTheDocument()`

To assert an element is *not* rendered, use `queryBy*` keyed on role + accessible name.

Do:

```ts
expect(
  screen.queryByRole('alert', { name: /failed/i }),
).not.toBeInTheDocument()
```

Don't:

```ts
expect(screen.getAllByRole('button')).toHaveLength(2)   // ❌ brittle proxy
```

Counting all matches of a role to mean "no extra control" breaks the moment an unrelated accessible element is added.

### Region-scoped status assertions

When a view contains multiple `role="status"` regions (or any duplicated landmark / live region), scope assertions to the specific region using `within(...)`, a container query, or a more specific accessible-name match.

Do:

```ts
const saveStatus = screen.getByRole('status', { name: /save status/i })
expect(within(saveStatus)).toHaveTextContent(/saved/i)
```

Don't:

```ts
expect(screen.getByText(/saved/i)).toBeInTheDocument()   // ❌ may match either region
```

### Verify rendered data, not only structure

For data-bearing views (tables, lists, charts, forms), assert on representative **data values** — cell contents, list items, summary numbers — not only on column headers, container roles, or row counts. Structure-only assertions silently pass when the data pipeline is broken.

Do:

```ts
const row = screen.getByRole('row', { name: /2055/ })
expect(within(row).getByText(/\$1,234,567/)).toBeInTheDocument()
```

Don't:

```ts
expect(screen.getAllByRole('row')).toHaveLength(31)   // ❌ structure only
```

### Behavioral input coverage

Every editable view MUST have at least one test that simulates a real user input (typing, clearing, selection) and asserts that the resulting **request body, derived state, or rendered output reflects the edit**. A test that round-trips server-provided data back to the server passes even if every input is ignored — that's not coverage.

Do:

```ts
const yaml = await waitForLoadedEditor()
await user.clear(yaml)
await user.type(yaml, 'age: 31\n')
await user.click(screen.getByRole('button', { name: /save/i }))
await waitFor(() => expect(captured?.content).toBe('age: 31\n'))
```

### Shared defaults; no duplicated literals

Hoist repeated network or render setup to `beforeEach` (or shared helpers / factories). Reference endpoint URLs and sample payloads through named constants, not re-typed string literals per test. Tests should declare only what differs from the default.

```ts
const ORIGIN = 'http://localhost:5173'
const CONFIG_URL = `${ORIGIN}/api/config`
const RUN_URL = `${ORIGIN}/api/simulation/run`

beforeEach(() => {
  server.use(http.get(CONFIG_URL, () => HttpResponse.json({ content: sampleYaml })))
})
```

### One observable behavior per test

A test name describes a single user-observable outcome. Titles that concatenate multiple behaviors with `and`, `;`, or `+` MUST be split. When one fails, the title should immediately tell you which behavior regressed.

Do:

```
it('shows an error when saving fails', ...)
it('clears the error after a successful save', ...)
```

Don't:

```
it('shows an error when saving fails and clears it on success', ...)
```

### No debug leftovers at merge

Test files MUST NOT contain `screen.debug()`, `console.log`, `debugger`, `it.only`, `describe.only`, `xit`, or `fit` at merge time. ESLint or pre-commit enforcement is recommended; today this is reviewer-enforced.

### Snapshots

Snapshot tests MAY be used **only** for small, stable, presentational output (e.g. an icon, a tiny formatter component). They MUST NOT substitute for behavior-focused tests on interactive or data-heavy views.

### Coverage and speed

- Coverage: ≥ 80% on new component code; primary user journeys (load, save, run simulation, error recovery) get integration-style coverage of all four UI states (loading / success / empty / error).
- Unit / component test: < 1 second.
- Whole frontend suite contributes to the < 5 minute overall budget.
- Browser-style E2E tests (if introduced) MUST be categorized so they don't silently slow the default `npm run test:run`.

## Frontend-specific guardrails

- NEVER introduce plain JavaScript application code under `src/`. TypeScript only. (Tooling configs like `eslint.config.js` are exempt.)
- NEVER add a heavyweight dependency without flagging it. Bundle size and install footprint matter.
- NEVER disable an ESLint rule or TypeScript check to make CI pass. Fix the underlying issue or escalate.
- NEVER call `fetch` directly from a component or hook outside `services/api.ts`.
- NEVER add a new endpoint to `services/api.ts` without a matching type in `types/api.ts`.
- NEVER commit `console.log` / `screen.debug` / `it.only` / `debugger` in test or app code.
- NEVER replace a behavior test with a snapshot to make a flaky test pass.
