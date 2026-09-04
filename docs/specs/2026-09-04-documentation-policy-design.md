# Documentation policy — ephemeral specs/plans, durable OVERVIEWs

**Date:** 2026-09-04  
**Status:** Approved

**GitHub:** track larger follow-on work with issues; this spec is the design for the policy cutover itself.

---

## 1. Goal

Specs and implementation plans are useful while a feature is open (especially specs during review) and harmful after it ships: they go stale, congest agent context, and duplicate what `AGENTS.md` / `OVERVIEW.md` already cover.

After this cutover:

- Durable agent context lives only in root/`nested` `AGENTS.md` and package/area `OVERVIEW.md`.
- Open designs live as committed specs under `docs/specs/` and are **deleted when the feature is done** (git history is enough).
- Implementation plans live under `docs/plans/` and are **gitignored**. After implementation, agents **recommend deleting** the local plan file.
- Roadmap / sequencing lives in **GitHub issues**, not an in-repo phase index.
- `archive/` and the current `docs/superpowers/`, `docs/ideas/`, and `docs/backlog/` trees are removed from the working tree.

### In scope

- New `docs/specs/` + `docs/plans/` layout and `.gitignore` rules
- Root `AGENTS.md` policy rewrite (repo map, artifact table, phase-planning rule, stale spec pointers)
- One-time deletion of `docs/superpowers/`, `docs/ideas/`, `docs/backlog/`, and `archive/`
- Pointer cleanup in remaining committed files (OVERVIEWs, scripts, nested `AGENTS.md`, README) so they do not cite deleted paths
- CI on `pull_request` and `push` to `main` that fails if `docs/specs/` has tracked files other than an allowlisted stub
- Explicit user confirmation already given to modify `.github/workflows/`

### Out of scope

- Rewriting package OVERVIEW *content* beyond dropping dead links / promoting a one-liner that would otherwise be lost
- Creating GitHub issues for historical rebuild phases
- Changing Cursor superpowers skills upstream; this repo’s `AGENTS.md` overrides paths and commit rules
- Recovering deleted docs except via git history when someone explicitly asks

---

## 2. Artifact roles

| Artifact | Role | Lifetime | Git |
| -------- | ---- | -------- | --- |
| Root / nested `AGENTS.md` | How to work in this repo or area | Permanent | committed |
| `packages/*/OVERVIEW.md` (and similar area overviews) | Durable context for that package | Permanent; update when shipped behavior agents must know changes | committed |
| GitHub issues | Roadmap and larger-work tracking | Outside the tree | n/a |
| Spec `docs/specs/YYYY-MM-DD-<topic>-design.md` | Design under review / while implementing | Exists only while work is open; delete when the feature is done | committed while open |
| Plan `docs/plans/YYYY-MM-DD-<topic>.md` | Step-by-step implementation checklist | Local working file; agents recommend deleting after implementation | **gitignored** |

**Promote before delete:** lasting policy or behavior notes must land in `AGENTS.md` or the relevant `OVERVIEW.md` *before* the spec is removed.

Do not create `docs/features/.../Development/` chains. Do not use `archive/`.

---

## 3. Layout after cutover

```
docs/
├── specs/                 # committed; open designs only
│   └── .gitkeep           # allowlisted stub when no spec is open
└── plans/
    └── README.md          # committed stub: local plans only; *.md plans are ignored
```

Naming:

- Specs: `docs/specs/YYYY-MM-DD-<topic>-design.md`
- Plans: `docs/plans/YYYY-MM-DD-<topic>.md`

`.gitignore` (replace the obsolete `docs/ideas/`, `docs/backlog/`, `docs/active/`, and `docs/features/*/Research/` entries with):

```
docs/plans/*.md
!docs/plans/README.md
```

Allowlist for an empty specs directory: **only** `docs/specs/.gitkeep`. No other tracked files.

---

## 4. Agent load rules

- Session start: load root `AGENTS.md` plus the nested `AGENTS.md` / `OVERVIEW.md` for the area being touched. **Do not** load a rebuild index (that file is deleted).
- Design / code review of open work: load the matching file under `docs/specs/` if present. Do **not** load a plan unless the task is to continue implementing that plan.
- After implementation completes: delete the spec in the same change set that lands the feature (or a last commit on the PR); **recommend deleting** the local plan file.
- Never load historical specs/plans or `archive/` unless the user explicitly asks (and after cutover those paths are gone; use git history).
- Do not auto-browse GitHub issues unless the user points at one.

Plans may be written by the writing-plans skill to `docs/plans/`. They must not be `git add`ed.

---

## 5. Root `AGENTS.md` changes

Replace, do not accumulate:

| Current | Replacement |
| ------- | ----------- |
| Repo map lines for `docs/superpowers/` and `archive/` | `docs/specs/` (open designs only) and `docs/plans/` (gitignored local plans). No `archive/`. |
| “See also” link to `docs/superpowers/specs/2026-06-28-phase-3a-plus-networked-market-data-design.md` §5 | Fold any still-needed operator facts into the existing Market data refresh section; drop the spec path. |
| **AI artifact policy** table | **Documentation policy** table matching §2. Include: delete spec on done; recommend deleting local plans; GitHub issues for roadmap; do not create `docs/features/` chains. |
| **Phase planning** (“load rebuild-index at session start”) | Remove. Point at GitHub issues for larger work and at `docs/specs/` only when a spec is open for the current task. |
| Testing-policy clause “unless a phase plan calls for…” | Rephrase to durable language (e.g. unless `AGENTS.md` or an *open* spec calls for a specific integration smoke test). |
| Package-dependency line “unless a later spec says so” | “unless an open spec or nested `AGENTS.md` says so”. |

Nested `AGENTS.md` files that say “unless a later spec says so” get the same wording pass.

---

## 6. One-time migration

Single implementation (not a gradual archive):

1. Delete the tracked trees `docs/superpowers/` and `archive/` entirely. Delete local `docs/ideas/` and `docs/backlog/` as well (they are gitignored today; do not leave them as a parallel docs system).
2. Do **not** copy old specs/plans into `docs/specs/`. Git history is the backup.
3. Create `docs/specs/.gitkeep`, `docs/plans/README.md` (explains gitignored `*.md` plans), and the `.gitignore` rules in §3.
4. Grep the remaining tree for `docs/superpowers`, `archive/`, `rebuild-index`, and `docs/features/` and fix or remove those pointers. Known committed hits outside the deleted trees include `AGENTS.md`, `packages/domain/OVERVIEW.md`, `scripts/refresh_market_data.py`, and possibly nested package `AGENTS.md` / READMEs.
5. In-flight work that still lived under `docs/superpowers/` (for example disability-insurance local config) is treated as complete or already captured in `tools/AGENTS.md` / helpers; those files die with the wipe. If durable behavior is missing from OVERVIEW/`AGENTS.md`, add it during pointer cleanup — do not keep the old spec.

This spec file (`docs/specs/2026-09-04-documentation-policy-design.md`) is the *open* spec for the cutover. **The last step of the cutover PR is to delete this spec** so `main` matches the CI rule. Promote any remaining policy sentences into `AGENTS.md` first (the `AGENTS.md` rewrite in §5 is that promotion).

---

## 7. CI

User confirmed workflow edits.

Add a job (or a first step that does not need `uv sync`) on the existing `.github/workflows/main_ci.yml` triggers (`push` to `main` and `pull_request`):

- After checkout, list **tracked** files under `docs/specs/` (e.g. `git ls-files 'docs/specs/**'`).
- Allowed: empty list, or only `docs/specs/.gitkeep`.
- Otherwise fail with a message that open specs must be deleted before the branch lands on `main` (PR **HEAD** must already be clean).

Run this independently of the Python test/lint job so a docs violation is obvious and cheap.

**Review workflow this implies:** a feature PR may contain a spec in earlier commits; CI looks at HEAD. Review implementation against the spec, then delete the spec (and recommend deleting the local plan) before merge.

---

## 8. Testing and verification

No pytest of markdown policy. Verification for the implementation plan:

- Grep: zero remaining references to `docs/superpowers`, `archive/`, or the rebuild index in committed files (except git history).
- `git check-ignore -v docs/plans/example.md` shows the plans ignore; `docs/plans/README.md` is not ignored.
- CI script/step fails when a dummy spec is tracked and passes with only `.gitkeep`.
- `AGENTS.md` repo map and documentation policy match §2–§5.

---

## 9. Error handling and edge cases

- **Plan accidentally staged:** agents must unstage / not commit `docs/plans/*.md`. CI does not need to police plans if gitignore holds.
- **Spec needed across multiple PRs:** keep the spec until the *feature* is done, not until the first PR. `main` must still be spec-empty, so either the work stays off `main` until done, or later PRs recreate a short-lived spec. Prefer one feature / one spec lifetime; split PRs should not leave a spec on `main`.
- **Someone needs an old design:** `git log --all -- docs/superpowers/specs/` (or `git show <commit>:path`). Do not restore files “just in case”.
