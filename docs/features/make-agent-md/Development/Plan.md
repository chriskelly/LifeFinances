---
name: speckit-to-agents-md
overview: Replace the Speckit constitution + tooling with a nested AGENTS.md set (root + backend + frontend), encode the proposed docs/ layout policy, and remove all Speckit infrastructure (the constitution is dropped, not archived).
todos:
  - id: draft-root-agents
    content: Draft root AGENTS.md (project overview, repo map, cross-stack commands, docs policy from reorg backlog, guardrails, pointers to nested files)
    status: completed
  - id: draft-backend-agents
    content: Draft backend/AGENTS.md (uv/ruff/pyright/pytest commands, Python Do/Don't snippets, API conventions, TDD + coverage rules, standalone-tools exception)
    status: completed
  - id: draft-frontend-agents
    content: Draft frontend/AGENTS.md (vite/vitest/lint commands, React architecture Do/Don't, full RTL+MSW+user-event TDD ruleset including the nine review-derived patterns, accessibility, four required UI states)
    status: completed
  - id: review-checkpoint
    content: Pause for user review of the three AGENTS.md drafts before any deletions
    status: completed
  - id: update-readme-gitignore
    content: Update README.md to point at AGENTS.md (drop any constitution reference); add docs/features/*/discovery/ to .gitignore
    status: completed
  - id: remove-speckit
    content: Delete .specify/ entirely, all .cursor/commands/speckit.*.md (9 files), and .cursor/rules/specify-rules.mdc
    status: completed
isProject: false
---

## Goal

Transition the project from Speckit-style governance (a single dense `constitution.md` plus `.specify/` templates and `.cursor/commands/speckit.*`) to the cross-tool AGENTS.md format documented at [agents.md](https://agents.md). The end state is three short, executable AGENTS.md files (one per stack), no Speckit infrastructure left in the repo (the constitution is dropped, not archived — AGENTS.md is the sole source of truth), and a baked-in docs/ folder policy taken from [docs/backlog/reorg-documentation/_overview.md](docs/backlog/reorg-documentation/_overview.md).

## Design choices (decided)

- **Three AGENTS.md files**, nested: `AGENTS.md` (root, cross-cutting policy), `backend/AGENTS.md` (Python/Flask), `frontend/AGENTS.md` (React/TS). Modern coding agents auto-walk up the tree, so an agent editing `backend/app/models/simulator.py` loads root + backend; one editing `frontend/src/App.tsx` loads root + frontend. This gives token-efficient scoping without requiring the user to do anything special.
- **No skills folder.** Skills are tool-specific (different in Cursor vs Claude Code vs Codex) and load on agent judgment rather than directory location, which is less reliable than nested AGENTS.md. Re-evaluate later if a topic is repeatedly missed.
- **Style**: terse, executable, "Do/Don't" snippets and command tables, per the [agents.md](https://agents.md/) "README for machines" guidance and the structure summarized in [docs/backlog/Make Agent.md/_overview.md](docs/backlog/Make%20Agent.md/_overview.md): persona/stack, project map, commands, code style with examples, workflow, guardrails.
- **Constitution is dropped, not archived**: per user direction. Every load-bearing rule must survive in AGENTS.md itself; if it isn't worth preserving in AGENTS.md, it's gone. This raises the bar for the frontend testing section in particular — the nine review-derived patterns must be expressed clearly enough in `frontend/AGENTS.md` to stand without an external rationale doc to point back to.
- **Docs policy** from the reorg backlog item is encoded in root AGENTS.md (idea/backlog/feature stages, `_overview.md` required, gitignored `discovery/`, no new top-level `specs/`).
- **Speckit removal is total**: `.specify/` (memory + templates + scripts), all `.cursor/commands/speckit.*.md`, and `.cursor/rules/specify-rules.mdc` are deleted. README is updated to drop Speckit references and point at AGENTS.md.

## File-by-file plan

### New files

- **[AGENTS.md](AGENTS.md)** — root, ~120-180 lines:
  - Project overview: simulator for personal finances/retirement, Flask + React monorepo
  - Tech stack snapshot (Python 3.10+, Flask 3.1, React 19, TypeScript 5.9, Vite 7, Vitest 4)
  - Repo map (one-screen tree of top-level + backend/app/* + frontend/src/*)
  - Cross-stack commands table: `make test`, `make lint`, `make`, `make coverage`, `pre-commit run --all-files`
  - Working directory contract: always run from repo root; `config.yml` resolves there; backend reads/writes `./config.yml`
  - Stack pointers: "When editing under `backend/`, also read [backend/AGENTS.md](backend/AGENTS.md). When editing under `frontend/`, also read [frontend/AGENTS.md](frontend/AGENTS.md)."
  - Documentation policy (from the reorg backlog):
    - `docs/ideas/` — disposable; `docs/backlog/` — proposed; `docs/features/<name>/` — active or completed
    - Every new initiative gets `_overview.md`
    - `discovery/` inside each feature is gitignored
    - New specs go under `docs/`, never top-level `specs/` (legacy `specs/` is frozen)
    - PR-oriented `specs/pr-N/` and `plans/pr-N/` subdirs allowed when one feature spans multiple PRs
  - Commit / PR conventions (small + reviewable; tests must pass; never `--no-verify` without justification)
  - Hard guardrails ("Never" list): never modify `.github/workflows/` without asking; never bypass pre-commit silently; never commit secrets or `config.yml` with real data; never edit auto-generated lockfiles by hand; never add new top-level `specs/` directories

- **[backend/AGENTS.md](backend/AGENTS.md)** — ~100-140 lines:
  - Stack: Python 3.10+, Flask 3.1, Pydantic 2.4, NumPy, pandas, PyYAML, pytest 9. Tooling: uv, ruff 0.14, pyright 1.1, pytest-cov, pytest-flask
  - Commands (run from repo root): `uv run --project backend pytest backend/tests`, `uv run --project backend ruff check backend`, `uv run --project backend ruff format --check backend`, `uv run --project backend pyright -p backend/pyrightconfig.json`, `uv run --project backend python backend/run.py`
  - Backend layout map: `backend/app/{models,routes,data,util.py}`, `backend/tests/` mirrors source, `backend/standalone_tools/` exempt from app testing rules
  - Code style — Do/Don't snippets:
    - Named function arguments (Do: `compute(user=u, year=2030)`, Don't: `compute(u, 2030)` for >1 arg)
    - Object models over dicts (Do: Pydantic/dataclass; Don't: untyped `dict[str, Any]`)
    - Type hints on every public function/method
    - Google or NumPy docstring style on modules and public APIs
    - No broad `except Exception` without inline justification comment
  - Routing/API conventions: `/api` prefix, JSON contracts under `backend/app/routes/api*.py`, response shape consistent with [docs/features/react-flask-migration/Development/contracts/openapi.yaml](docs/features/react-flask-migration/Development/contracts/openapi.yaml)
  - Testing rules:
    - TDD red-green-refactor; tests written before implementation
    - pytest only; mirror source tree in `backend/tests/`
    - Shared setup via `conftest.py` fixtures; explicit collaborator wiring (no hidden globals)
    - Test names describe domain behavior, not implementation
    - Unit <1s, integration <10s, suite <5min
    - Coverage: 80% on new code; 95% on financial calc / state transitions / simulator core
    - Standalone scripts/notebooks exception only for `backend/standalone_tools/*` and ad-hoc `*.ipynb` not imported by app code
  - Performance: profile with cProfile; `make profile` target exists; simulation trial target <100ms
  - Guardrails: never delete or rewrite `backend/app/data/variable_statistics.csv` without confirmation; never introduce new dependencies without bumping `backend/pyproject.toml` and running `uv sync`

- **[frontend/AGENTS.md](frontend/AGENTS.md)** — ~150-200 lines (densest, since the React TDD section is load-bearing):
  - Stack: React 19, TypeScript 5.9 (strict), Vite 7, Vitest 4, React Testing Library, @testing-library/user-event, MSW 2, jsdom. Node engines pinned in `frontend/package.json`
  - Commands (run from `frontend/`): `npm run dev` (port 5173), `npm run test:run`, `npm run test` (watch), `npm run lint`, `npm run build`
  - Frontend layout map: `frontend/src/{App.tsx,main.tsx,services/,types/,test/,assets/}`, tests colocated as `*.test.tsx` next to source
  - Architecture — Do/Don't:
    - Composition over monoliths (split data fetching / orchestration / presentation)
    - State stays local; treat server state, derived UI state, transient interaction state as separate
    - Typed API boundary centralized in [frontend/src/services/api.ts](frontend/src/services/api.ts) with shapes in [frontend/src/types/api.ts](frontend/src/types/api.ts)
    - Feature-oriented organization; reusable primitives kept separate from feature components
    - Accessibility default: semantic HTML, keyboard ops, explicit labels, visible focus; placeholder is never the only label
    - Required UI states for any data view: loading / success / empty / error (all four)
    - Named option objects over long positional arg lists
  - Testing — the load-bearing section, in compressed Do/Don't form covering all nine review-derived patterns from constitution v1.6.0:
    - **Testing Library first**: query by `getByRole(name)`, `getByText`, accessible names; `data-testid` only with justification
    - **Realistic interaction**: `@testing-library/user-event`, not `fireEvent`
    - **Network boundary**: MSW `http.*` only; never spy on or replace `fetch`
    - **Handler purity**: handlers shape responses; assertions live in test body against captured request data — never `expect(...)` inside a handler (it surfaces as opaque network error)
    - **Async**: `findBy*` / `waitFor` / async user-event; never `setTimeout` waits in handlers or tests
    - **Determinism**: in-flight UI exercised via deferred promises the test resolves explicitly, or fake timers
    - **Negative presence**: `queryBy*(...).not.toBeInTheDocument()` keyed on role+name; never use `getAllByRole(...).length` as a "no extra control" proxy
    - **Region-scoped status**: when multiple `role="status"` regions exist, scope with `within(...)` or specific accessible name
    - **Verify rendered data, not only structure**: assert on cell contents / list items / summary numbers; column headers and row counts alone are insufficient
    - **Behavioral input coverage**: at least one test per editable view simulates real user input and asserts the resulting request body or output
    - **Shared defaults**: hoist setup to `beforeEach` and named URL/payload constants; tests declare only what differs
    - **One observable behavior per test**: titles describe a single outcome; split any title containing "and"/`;`/`+`
    - **No debug leftovers**: no `screen.debug()`, `console.log`, `debugger`, `it.only`, `describe.only` at merge
    - **Hooks**: test with `renderHook` + explicit provider wrappers matching production
    - **Snapshots**: small stable presentational only; never the primary assertion for interactive views
  - For each pattern, include a one-line "why" inline (e.g. "an `expect` thrown inside a handler surfaces to the component as an opaque network error") so the rule survives without an external rationale doc.
  - Guardrails: never introduce JavaScript application code (TS only); never add a heavy dependency without flagging; never disable lint/type-check rules to pass CI

### Modified files

- **[README.md](README.md)** — minor edits:
  - Add a one-liner under "Developer Setup" pointing agents/humans at `AGENTS.md` for project conventions
  - Remove any line that references the constitution as the source of governance

- **[.gitignore](.gitignore)** — add `docs/features/*/discovery/` (per docs policy)

### Deleted files

- `.specify/memory/constitution.md` (dropped; not archived)
- `.specify/templates/` (5 files: agent-file-template.md, plan-template.md, spec-template.md, tasks-template.md, checklist-template.md)
- `.specify/scripts/bash/` (5 scripts)
- The `.specify/` directory entirely
- `.cursor/commands/speckit.analyze.md`, `speckit.checklist.md`, `speckit.clarify.md`, `speckit.constitution.md`, `speckit.implement.md`, `speckit.plan.md`, `speckit.specify.md`, `speckit.tasks.md`, `speckit.taskstoissues.md` (9 files)
- `.cursor/rules/specify-rules.mdc`

## Review flow

I will produce the three AGENTS.md files as a draft set in one pass, plus the README/.gitignore edits. You review the drafts, request edits, and only after sign-off do I delete the Speckit infrastructure (including the constitution itself). That keeps the destructive step last and reversible — until I delete `.specify/memory/constitution.md`, the original is still on disk if you decide a section needs to come back into AGENTS.md.

## Out of scope (explicitly)

- Maintaining `docs/features/` as the canonical home for spec/plan artifacts and forbidding new top-level `specs/` content.
- Authoring a docs-management skill (also in the reorg backlog) — wait until the AGENTS.md policy has shaken out.
- Cleaning up `temporary.ipynb`, `htmlcov/`, `__pycache__/` and other repo hygiene.
- Updating any feature plans currently in flight.