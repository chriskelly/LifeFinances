# Simulation — Agent Guide

Monthly TPAW withdrawal engine. Depends on `domain` and `core`; never imports
`web`.

## Rules

- Resolve planning assumptions from the same `Plan` you pass to `build_return_paths`.
- TPAW goldens are pinned contract values; never retune them to pass a refactor.

## Reference

- TPAW parity, numerical caveats, and testing approach → `packages/simulation/docs/parity.md`
- Pipeline walkthrough → `packages/simulation/README.md`
