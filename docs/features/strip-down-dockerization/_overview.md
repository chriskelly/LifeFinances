# Strip down Dockerization

Status: Active feature — design approved, awaiting plan
Source: promoted from `docs/ideas/Consider stripping down Dockerization/`

## Goal

Stop maintaining the `docker compose` stack that exists only for local "try it out" runs (no users, no deployment), and use the existing devcontainer image as the CI runner so local dev and CI run inside the same image.

## Scope

One feature, one PR, three coordinated changes:

1. **Strip the Compose stack.** Delete `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, and the Compose branches of `Makefile`.
2. **Adopt the devcontainer image as the CI runner** via `devcontainers/ci@v0.3` with GHCR layer caching.
3. **Rewrite the README** for devcontainer-first onboarding (drop the "Run with Docker" section).

Plus this docs reorganization itself: the idea has moved into `docs/features/strip-down-dockerization/`.

## Out of scope

- Constitution amendments (constitution is silent on container/CI tooling).
- Production / deploy images (no users, no deploy target).
- Renaming the reorg-documentation backlog's proposed `discovery/` directory (this feature uses `Research/` for the same role; cross-project naming alignment is a separate decision).
- Historical `docs/features/react-flask-migration/` Docker mentions (kept as record of how things were).

## Pointers

- **Spec:** [`Development/spec.md`](Development/spec.md)
- **Plan:** `Development/plan.md` *(produced by writing-plans skill after spec approval)*
- **Local research notes:** `Research/` *(gitignored; not part of the public record)*

## Next action

User reviews `Development/spec.md`, then we invoke the writing-plans skill to produce `Development/plan.md`.
