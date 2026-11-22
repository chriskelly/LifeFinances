# Numerical validation against TPAW

Scope: how simulation correctness is validated without a runnable TPAW binary,
and how to diagnose a gap against a real plan. Read before changing parity
goldens or investigating a mismatch. Parity behavior and input mapping:
`parity.md`.

Validation targets algorithmic parity, not bit-identical output; see
`parity.md` (Numerical parity caveat).

## Testing approach: doctest-golden values

There is no runnable TPAW binary in this repo to diff full simulation runs
against, so correctness is validated in two layers:

1. **Unit goldens pinned to TPAW's own test cases.** The pure-math modules have
   tests whose expected values are copied from TPAW's own doctests/test cases
   and checked with a tolerance rather than exact equality:
   `../simulation/mertons.py` (plain/effective Merton's formula,
   `get_rra_for_all_stocks`), `../simulation/risk.py` (risk-tolerance → RRA
   endpoints), `../simulation/npv.py` (backward precomputation, target
   withdrawals with no ceiling/floor, stock allocation), and
   `../simulation/withdrawals.py` (`apply_contributions_and_withdrawals`,
   `apply_allocation`). These literals are intentionally pinned contract
   values, comment-marked with the TPAW test they were sourced from (for
   example `# pinned: tpaw mertons_formula.cu plain_mertons_formula TEST_CASE`).
2. **Deterministic end-to-end sanity checks.** Full-simulation correctness is
   checked with deterministic (no network, no live market data),
   constant-return scenarios: money-conservation checks (nothing is created or
   destroyed across a run), zero-income behavior, and monotonicity spot-checks
   (a run with better returns should never do worse than one with worse
   returns, all else equal).

Together, these confirm that each formula matches TPAW's reference values and
that the assembled pipeline behaves sensibly, even though no full end-to-end
numerical diff against TPAW is possible.

## Investigating a gap against a real TPAW plan

When the two disagree, the cause may be an input mismatch (cheaper to debug)
rather than engine math. Work in this order.

**Compare month 0 first.** The first month is identical across Monte Carlo
runs, so a month-0 gap cannot come from sampling, the RNG, or the
historical-returns adjustment. Read the later months only once month 0 agrees.

**Diff the inputs, most sensitive first:** portfolio balance; risk (tolerance
at 20, glide to max age, legacy delta, time preference, additional annual
spending tilt); planning-return preset and log-volatility scales; inflation;
sampling; horizon. For the risk block, use the mapping table in `parity.md` —
TPAW's UI shows the glide decrease and Preference for the Future; both are the
negation of TPAW's stored values.

**Take TPAW's values from an exported plan.** Plan menu → *Save to File*
writes a `.tpaw.txt`: prose header, then JSON from the first `{`. The payload
is a JSON-patch **history**, not a params snapshot — replay
`planParamsHistory[].diff` in order over an empty object (only `add`,
`replace`, and `remove` appear in practice); `reverseHeadIndex: 0` means the
last entry is the current state. The head's `timestamp` is the plan's
**evaluation date**: run LifeFinances with `today` set to it, because planning
returns come from that date's CAPE and TIPS data.

**Expect these mapping differences.** TPAW has no tax model — its
`futureSavings` and `incomeDuringRetirement` are net amounts, while
LifeFinances builds gross job/SS/pension income and taxes it; compare
annualized `income_real` against the stream schedule and accept a few percent
of drift. TPAW's `startAndDuration` extra-spending windows are durations, while
LifeFinances includes both the start and end months; a 12-month TPAW sabbatical
becomes 13 months in LifeFinances if the end is copied literally. TPAW's month
count includes the max-age month, so a tail difference can be the horizon
rather than the math. TPAW's chart percentile set and run count are not in the
exported params, so do not treat a band difference as engine drift; compare
month 0 and the summary scalars first.

**Mutate copies.** Ablate parameters on a copy of the plan — never the stored
plan or the exported TPAW params.

**Sensitivity, for triage on a long-horizon plan with real returns near 3%:** a
0.5%/yr additional spending tilt moves month-0 spending by roughly 12%, a
1.0-point time-preference mismatch by roughly 7–8%, a risk-tolerance glide of
2 points by roughly 5%, and one horizon month by roughly 0.1%. Tilt, time
preference, and glide mismatches are large enough to explain a four-figure
monthly gap on their own.

**Worked example.** A plan carrying a −0.5%/yr additional tilt and a flat
glide, compared against TPAW with tilt 0 and a 2-point glide, differed by
~$1k/month at month 0 and matched once both inputs were aligned, with no engine
change. A second plan showed $14,041 at month 0 with
`time_preference = -0.005` and $15,028 with `time_preference = +0.005`; the
TPAW export carried the positive rate and charted $14,952. Aligning the sign
moved month 0 to within $76 (0.5%) of TPAW, leaving only the usual
net-income/tax drift.
