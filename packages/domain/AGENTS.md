# Domain — Agent Guide

Income, spending, tax, and Social Security logic that produces monthly
cashflows. Depends only on `core`; never imports `web` or `simulation`.

## Rules

- Build income and spending from `core.streams.TimedStream`; do not add a second stream primitive.
- `is_nominal` is the only basis switch; future-dated nominal anchoring is not supported.
- Single-person plans set `Household.person2 = None`; do not special-case them outside `Household`.

## Reference

- Stream semantics and household handling → `packages/domain/docs/models.md`
