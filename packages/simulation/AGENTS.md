# Simulation — Agent Guide

Monthly TPAW withdrawal engine. Depends on `domain` and `core`; never imports
`web`.

## Rules

- Resolve planning assumptions from the same `Plan` you pass to `build_return_paths`.
- Use `resolve_assumptions` for display-only assumption summaries; do not run the engine to read them.
- TPAW goldens are pinned contract values; never retune them to pass a refactor.
- Keep the mechanism walkthrough in the package README as the human-facing
  long-form explanation; it has no line budget. The `docs/` leaves remain the
  agent references; do not move or restate the walkthrough in one.
- Roadmap status for TPAW parity lives in GitHub issues; the parity docs record
  current behavior only.

## Reference

- TPAW parity and input mapping → `packages/simulation/docs/parity.md`
- Numerical validation and gap diagnosis → `packages/simulation/docs/numerical-validation.md`
- Mechanism walkthrough → `packages/simulation/README.md`
- Display-only assumptions entrypoint → `packages/simulation/docs/assumptions.md`
