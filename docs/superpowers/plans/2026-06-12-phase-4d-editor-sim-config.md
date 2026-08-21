# Phase 4d — Spending & Simulation Config Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make spending goals and all persisted simulation controls editable in the split-pane web UI, while showing the exact resolved assumptions used by the current cached simulation.

**Architecture:** Add four section-scoped HTMX forms—Spending goals, Risk, Market assumptions, and Simulation details—using the Phase 4c full-section merge pattern. Correct per-stream spending basis conversion in preprocessing, retain resolver provenance, and attach one required `ResolvedAssumptions` snapshot to `SimulationResult`; the results response updates the Market assumptions summary out-of-band so charts and displayed assumptions always come from one cached run.

**Tech Stack:** Python 3.14+, Pydantic 2, NumPy, FastAPI, Jinja2, HTMX, plain JavaScript, SQLite, pytest, ruff, pyright, uv workspace.

## Global Constraints

- Run every command from the repository root: `/Users/chris/Projects/life-finances-workspace/LifeFInances`.
- Follow TDD for every behavior. Write the test first, add minimal scaffolding for new symbols, and run once only after failures can be **logical** (`AssertionError`, `NotImplementedError`, wrong value, or an expected exception not raised). Structural failures (`ImportError`, `AttributeError`, `NameError`, `ModuleNotFoundError`) do not count as red; add scaffolding and rerun until the test reaches behavior.
- Never hardcode the same literal in arrange and assert. Bind shared values once. Import defaults, thresholds, labels, and configuration constants from production modules.
- Test one logical behavior per test. Keep arrange, act, and assert visually distinct.
- Inject `today`, `now`, `ran_at`, resolvers, and fetchers. Tests must not read wall-clock time or perform real network requests.
- Test application logic, not Pydantic/library behavior alone. A model-validation assertion is included only when it proves our validator wiring or a Phase 4d contract.
- Form DTOs are transport-only. Do not add Pydantic `Field` constraints to web DTOs; build `core.models` objects and let core validation decide validity.
- HTML field names come from `web.forms` constants. Indexed names are formed from exported prefixes and suffixes; templates must not invent independent wire names.
- Package direction stays strict: `web → simulation, domain, core`; `simulation → domain, core`; `core → stdlib + pydantic + sqlite`.
- Do not add `TimedStream.id` in this phase. Stable stream identity remains a Phase 4e design decision.
- Do not expose historical sequential sampling, spending floor/ceiling, rich legacy sources, or bootstrapped inflation paths.
- Do not edit lockfiles by hand, `.github/workflows/`, `config.yml`, or `data/data.db`.
- Use underscores in large numeric literals.
- Each task ends with targeted tests, the relevant package suite, and a focused Conventional Commit. Run full `make` in Task 10.

**Design spec:** [`docs/superpowers/specs/2026-08-21-phase-4d-editor-spending-simulation-config-design.md`](../specs/2026-08-21-phase-4d-editor-spending-simulation-config-design.md)

## File structure

| File | Responsibility |
| ---- | -------------- |
| `packages/core/core/models.py` | Reject duplicate percentiles; continue sorting and range validation |
| `packages/core/tests/test_advanced_config.py` | Core percentile contract |
| `packages/simulation/simulation/market_data/inflation.py` | Preserve T10YIE market source and observation date |
| `packages/simulation/simulation/planning_returns.py` | Preserve only the S&P/Treasury provenance consumed by the active preset |
| `packages/simulation/simulation/preprocess.py` | Convert real/nominal spending per stream; retain resolver outputs |
| `packages/simulation/simulation/result.py` | Define `ResolvedAssumptions`; require it on public results |
| `packages/simulation/simulation/aggregate.py` | Carry assumptions into `SimulationResult` |
| `packages/simulation/simulation/stub.py` | Build the snapshot from the same resolver outputs used by preprocessing |
| `packages/simulation/tests/` | Resolver provenance, spending basis, snapshot, aggregate, and result tests |
| `packages/web/web/forms.py` | Phase 4d form constants, parsers, DTOs, labels, and merge logic |
| `packages/web/web/routes.py` | Four editor GET and four plan PATCH path constants |
| `packages/web/web/sections.py` | Four section titles |
| `packages/web/web/app.py` | Phase 4d GET/PATCH handlers and assumptions context |
| `packages/web/web/resolved_assumptions.py` | Display-only source labels and stock-volatility formatting |
| `packages/web/web/templates/editor_spending.html` | Two timed-stream lists plus scalar legacy target |
| `packages/web/web/templates/editor_risk.html` | Visible and advanced risk controls |
| `packages/web/web/templates/editor_market_assumptions.html` | Inflation, seven return presets, conditional fields, initial summary |
| `packages/web/web/templates/editor_simulation_details.html` | Collapsed sampling and percentile controls |
| `packages/web/web/templates/_resolved_assumptions.html` | Shared initial/OOB assumptions summary |
| `packages/web/web/templates/index.html` | Include Phase 4d sections and conditional script |
| `packages/web/web/templates/results.html` | OOB assumptions replacement on success and failure |
| `packages/web/web/static/editor_lists.js` | Generic indexed-row reminting for every `data-prefix` list |
| `packages/web/web/static/editor_conditional.js` | Conditional visibility and HTML-required state |
| `packages/web/tests/` | One focused test module per section plus assumptions summary tests |
| `packages/web/AGENTS.md` | Document Phase 4d conditional controls and OOB summary contract |
| `docs/superpowers/plans/2026-06-12-rebuild-index.md` | Mark 4d exit criteria complete after verification |

## Delivery grouping

The tasks are ordered by dependency and may be delivered as one branch. If review size exceeds the repository guidance, split only at green commit boundaries:

- **4d-1 — Spending:** Task 2 (basis correction) and Task 6 (Spending goals editor).
- **4d-2 — Simulation config:** Tasks 1, 3–5, and 7–10.

Task numbers remain the execution order for a single branch. For a split delivery, cherry-pick the focused Task 2 and Task 6 commits into 4d-1; neither depends on the config tasks.

---

### Task 1: Reject duplicate output percentiles in core

**Files:**
- Modify: `packages/core/core/models.py:65-79`
- Modify: `packages/core/tests/test_advanced_config.py`

**Interfaces:**
- Produces: `normalize_percentiles(value: list[int]) -> list[int]`, which rejects empty, duplicate, or out-of-range input and returns ascending unique values.
- Consumed by: `AdvancedConfig`, `run_simulation`, and Task 9's web percentile parser.

- [ ] **Step 1: Write the failing duplicate-contract tests**

Add:

```python
from pydantic import ValidationError


def test_normalize_percentiles_rejects_duplicates() -> None:
    duplicate = 50
    values = [5, duplicate, duplicate, 95]

    with pytest.raises(ValueError, match="duplicates"):
        normalize_percentiles(values)


def test_advanced_config_applies_duplicate_rejection() -> None:
    duplicate = 25

    with pytest.raises(ValidationError, match="duplicates"):
        AdvancedConfig(percentiles=[duplicate, duplicate])
```

These tests verify our normalization rule and the validator's delegation to it. Keep the existing sort, empty, and range tests unchanged.

- [ ] **Step 2: Run the new tests and confirm a logical red**

Run:

```bash
uv run pytest packages/core/tests/test_advanced_config.py::test_normalize_percentiles_rejects_duplicates packages/core/tests/test_advanced_config.py::test_advanced_config_applies_duplicate_rejection -v
```

Expected: both fail because no exception is raised. This is a logical failure; no scaffolding is needed because the function already exists.

- [ ] **Step 3: Implement duplicate rejection**

Update `normalize_percentiles`:

```python
def normalize_percentiles(value: list[int]) -> list[int]:
    if not value:
        raise ValueError("percentiles must be non-empty")
    if len(set(value)) != len(value):
        raise ValueError("percentiles must not contain duplicates")
    if any(p < 0 or p > 100 for p in value):
        raise ValueError("each percentile must be in 0..100")
    return sorted(value)
```

- [ ] **Step 4: Verify green**

Run:

```bash
uv run pytest packages/core/tests/test_advanced_config.py -v
uv run pytest packages/core -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_advanced_config.py
git commit -m "fix(core): reject duplicate simulation percentiles"
```

---

### Task 2: Honor each spending stream's real/nominal basis

**Files:**
- Modify: `packages/simulation/simulation/preprocess.py:57-66,117-124,214-239`
- Modify: `packages/simulation/tests/test_preprocess.py`

**Interfaces:**
- Produces: `_stream_to_real(stream: TimedStream, timeline: Timeline, *, deflator: np.ndarray) -> np.ndarray`.
- Produces: `_sum_streams_real(streams: Sequence[TimedStream], timeline: Timeline, *, deflator: np.ndarray) -> np.ndarray`.
- Contract: real streams (`is_nominal=False`) pass through projected face amounts; nominal streams divide by the monthly inflation deflator before category summation.

- [ ] **Step 1: Write three failing behavior tests**

Add imports:

```python
from core.models import InflationConfig
from core.streams import CalendarMonthBoundary, TimedStream
from simulation.market_data.inflation import annual_to_monthly
```

Add a focused helper and tests:

```python
def _spending_plan(*, streams: list[TimedStream], annual_inflation: Decimal):
    plan = default_plan()
    plan.inflation = InflationConfig(
        mode="manual", manual_annual_rate=annual_inflation
    )
    plan.extra_essential_spending = streams
    return plan


def test_real_essential_spending_is_not_deflated() -> None:
    amount = Decimal("1_000")
    annual_inflation = Decimal("0.12")
    today = date(2026, 1, 1)
    sample_month = 12
    stream = TimedStream(
        monthly_amount=amount,
        start=CalendarMonthBoundary(year=today.year, month=today.month),
        is_nominal=False,
    )

    processed = preprocess(
        _spending_plan(streams=[stream], annual_inflation=annual_inflation),
        today=today,
    )

    assert processed.essential_real[sample_month] == pytest.approx(float(amount))


def test_nominal_essential_spending_is_deflated() -> None:
    amount = Decimal("1_000")
    annual_inflation = Decimal("0.12")
    today = date(2026, 1, 1)
    sample_month = 12
    monthly_inflation = annual_to_monthly(float(annual_inflation))
    expected = float(amount) / ((1.0 + monthly_inflation) ** sample_month)
    stream = TimedStream(
        monthly_amount=amount,
        start=CalendarMonthBoundary(year=today.year, month=today.month),
        is_nominal=True,
    )

    processed = preprocess(
        _spending_plan(streams=[stream], annual_inflation=annual_inflation),
        today=today,
    )

    assert processed.essential_real[sample_month] == pytest.approx(expected)


def test_mixed_spending_streams_are_converted_before_summing() -> None:
    real_amount = Decimal("1_000")
    nominal_amount = Decimal("500")
    annual_inflation = Decimal("0.12")
    today = date(2026, 1, 1)
    sample_month = 12
    monthly_inflation = annual_to_monthly(float(annual_inflation))
    deflator = (1.0 + monthly_inflation) ** sample_month
    expected = float(real_amount) + float(nominal_amount) / deflator
    start = CalendarMonthBoundary(year=today.year, month=today.month)
    streams = [
        TimedStream(monthly_amount=real_amount, start=start, is_nominal=False),
        TimedStream(monthly_amount=nominal_amount, start=start, is_nominal=True),
    ]

    processed = preprocess(
        _spending_plan(streams=streams, annual_inflation=annual_inflation),
        today=today,
    )

    assert processed.essential_real[sample_month] == pytest.approx(expected)
```

- [ ] **Step 2: Run the tests and confirm logical red**

Run:

```bash
uv run pytest packages/simulation/tests/test_preprocess.py::test_real_essential_spending_is_not_deflated packages/simulation/tests/test_preprocess.py::test_nominal_essential_spending_is_deflated packages/simulation/tests/test_preprocess.py::test_mixed_spending_streams_are_converted_before_summing -v
```

Expected: real-only and mixed tests fail by numeric assertion; nominal-only passes under the old blanket-deflation behavior. The mixed test is the required regression red.

- [ ] **Step 3: Implement per-stream conversion**

Replace `_sum_streams` with:

```python
def _stream_to_real(
    stream: TimedStream,
    timeline: Timeline,
    *,
    deflator: np.ndarray,
) -> np.ndarray:
    projected = _decimal_series_to_float64(project_stream(stream, timeline))
    if stream.is_nominal:
        return projected / deflator
    return projected


def _sum_streams_real(
    streams: Sequence[TimedStream],
    timeline: Timeline,
    *,
    deflator: np.ndarray,
) -> np.ndarray:
    total = np.zeros(timeline.horizon_months, dtype=np.float64)
    for stream in streams:
        total += _stream_to_real(stream, timeline, deflator=deflator)
    return total
```

Replace category-level division in `preprocess`:

```python
essential_real = _sum_streams_real(
    plan.extra_essential_spending, timeline, deflator=deflator
)
discretionary_real = _sum_streams_real(
    plan.extra_discretionary_spending, timeline, deflator=deflator
)
```

Do not alter domain/manual-income deflation in this task; the approved 4d scope is spending streams.

- [ ] **Step 4: Verify green**

Run:

```bash
uv run pytest packages/simulation/tests/test_preprocess.py -v
uv run pytest packages/simulation -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/preprocess.py packages/simulation/tests/test_preprocess.py
git commit -m "fix(simulation): honor spending stream inflation basis"
```

---

### Task 3: Retain resolved inflation provenance

**Files:**
- Modify: `packages/simulation/simulation/market_data/inflation.py`
- Modify: `packages/simulation/tests/market_data/test_inflation.py`
- Verify: `packages/simulation/tests/market_data/test_public_api.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class InflationResolved:
    annual: float
    monthly: float
    source: Literal["suggested", "manual"]
    market_source: MarketDataSource | None = None
    observation_date: date | None = None
```

- `source` keeps its existing mode meaning. `market_source` is `"live"`, `"cache"`, or `"vendored"` only for Suggested mode.

- [ ] **Step 1: Extend tests to specify metadata behavior**

In existing suggested/manual/cache/refresh/fallback tests, bind expected dates and add:

```python
assert resolved.observation_date == expected_observation_date
assert resolved.market_source == expected_market_source
```

Add the focused manual test:

```python
def test_manual_inflation_has_no_market_provenance() -> None:
    annual_rate = Decimal("0.031")
    plan = default_plan()
    plan.inflation = InflationConfig(
        mode="manual", manual_annual_rate=annual_rate
    )

    resolved = resolve_inflation(plan)

    assert resolved.source == "manual"
    assert resolved.observation_date is None
    assert resolved.market_source is None
```

Use each test's existing temporary cache/vendored paths and injected `today`/`now`; do not add real I/O beyond those fixtures.

- [ ] **Step 2: Add structural fields without metadata logic**

Import `MarketDataSource` and extend the dataclass exactly as shown in Interfaces, leaving both new fields defaulted to `None`. Do not change `_suggested_annual` yet. Existing constructors continue to run, while Suggested-mode tests reach their new assertions and fail logically because provenance is absent.

- [ ] **Step 3: Run focused tests and confirm logical red**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py -v
```

Expected: numeric tests remain green; new provenance assertions fail because Suggested mode reports missing or wrong metadata. No constructor/import failure is acceptable.

- [ ] **Step 4: Implement source/date propagation**

Refactor `_suggested_annual`:

```python
def _suggested_annual(today: date, path: Path) -> tuple[float, date]:
    best_date: date | None = None
    best_value: Decimal | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                observed = date.fromisoformat(row[0].strip())
                percent = Decimal(row[1].strip())
            except ValueError, ArithmeticError:
                continue
            if observed > today:
                continue
            if best_date is None or observed > best_date:
                best_date = observed
                best_value = percent
    if best_value is None or best_date is None:
        raise ValueError(f"no T10YIE observation at or before {today.isoformat()}")
    annual = float(_round_half_away(best_value / Decimal(100)))
    return annual, best_date
```

Refactor `_resolve_t10yie_path` to return `tuple[Path, bool]`. Initialize `refreshed_live = False` after choosing `read_path`; set it to `True` only after a non-empty fetch is written successfully. Every existing early/final `return read_path` becomes `return read_path, refreshed_live`. This exact return contract lets `resolve_inflation` reset the flag to `False` when a cache read later falls back to vendored data.

Add the same source classification used by S&P/Treasury:

```python
def _market_source(
    *,
    refreshed_live: bool,
    read_path: Path,
    cache_path: Path,
) -> MarketDataSource:
    if refreshed_live:
        return "live"
    if read_path == cache_path and cache_path.is_file():
        return "cache"
    return "vendored"
```

In `resolve_inflation`, Manual sets both metadata fields to `None`. Suggested unpacks `(annual, observation_date)`, uses the final fallback path to classify `market_source`, and resets `refreshed_live=False` if it falls back from cache to vendored.

- [ ] **Step 5: Verify green**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py packages/simulation/tests/market_data/test_public_api.py -v
uv run pytest packages/simulation/tests/market_data -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/simulation/simulation/market_data/inflation.py packages/simulation/tests/market_data/test_inflation.py
git commit -m "feat(simulation): retain inflation source metadata"
```

---

### Task 4: Retain planning-return market provenance

**Files:**
- Modify: `packages/simulation/simulation/planning_returns.py`
- Modify: `packages/simulation/tests/test_planning_returns.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class PlanningReturns:
    annual_stocks: float
    annual_bonds: float
    annual_stock_log_variance: float
    sp500: SP500Resolved | None = None
    treasury: TreasuryYieldsResolved | None = None
```

- Provenance objects are present only if the selected preset actually consumes that feed.

- [ ] **Step 1: Write provenance tests using injected resolvers**

Reuse the file's resolver spy pattern and add:

```python
def test_regression_preset_retains_both_market_sources() -> None:
    sp500_date = date(2026, 4, 1)
    treasury_date = date(2026, 4, 2)
    expected_sp500 = SP500Resolved(
        close=6_000.0, observation_date=sp500_date, source="cache"
    )
    expected_treasury = TreasuryYieldsResolved(
        yields={TWENTY_YEAR_TENOR: 0.018},
        observation_date=treasury_date,
        source="vendored",
    )
    plan = default_plan()
    plan.planning_returns.preset = "regression_prediction"

    resolved = resolve_planning_returns(
        plan,
        sp500_resolver=lambda **_: expected_sp500,
        treasury_resolver=lambda **_: expected_treasury,
    )

    assert resolved.sp500 == expected_sp500
    assert resolved.treasury == expected_treasury


@pytest.mark.parametrize("preset", ["historical", "fixed"])
def test_non_market_presets_have_no_market_provenance(preset: PlanningPreset) -> None:
    plan = default_plan()
    plan.planning_returns.preset = preset

    resolved = resolve_planning_returns(
        plan,
        sp500_resolver=_resolver_that_fails_if_called,
        treasury_resolver=_resolver_that_fails_if_called,
    )

    assert resolved.sp500 is None
    assert resolved.treasury is None
```

Define the fail-fast resolver used above:

```python
def _resolver_that_fails_if_called(**kwargs):
    raise AssertionError(f"resolver must not be called; got {kwargs}")
```

Also add a fixed-equity-premium test asserting Treasury is present and S&P is absent, and a Custom test whose chosen bases consume both feeds.

- [ ] **Step 2: Add structural fields only**

Extend `PlanningReturns` with optional `sp500` and `treasury` fields. Leave the returned values as `None`.

- [ ] **Step 3: Run focused tests and confirm logical red**

Run:

```bash
uv run pytest packages/simulation/tests/test_planning_returns.py -v
```

Expected: existing numeric/call-count tests pass; market-preset provenance assertions fail because returned fields are `None`. No structural failure is acceptable.

- [ ] **Step 4: Memoize full resolver objects and return consumed provenance**

Replace scalar caches with:

```python
sp500_cache: SP500Resolved | None = None
treasury_cache: TreasuryYieldsResolved | None = None

def sp500_resolved() -> SP500Resolved:
    nonlocal sp500_cache
    if sp500_cache is None:
        sp500_cache = sp500_resolver(
            today=today,
            allow_refresh=allow_refresh,
            now=now,
            api_key=eod_api_key,
        )
    return sp500_cache

def treasury_resolved() -> TreasuryYieldsResolved:
    nonlocal treasury_cache
    if treasury_cache is None:
        treasury_cache = treasury_resolver(
            today=today, allow_refresh=allow_refresh, now=now
        )
    return treasury_cache
```

Use `sp500_resolved().close` and `treasury_resolved().yields[TWENTY_YEAR_TENOR]` in existing calculations. Return the two caches:

```python
return PlanningReturns(
    annual_stocks=annual_stocks,
    annual_bonds=annual_bonds,
    annual_stock_log_variance=variance,
    sp500=sp500_cache,
    treasury=treasury_cache,
)
```

Because resolution remains lazy, unused feed caches stay `None`.

- [ ] **Step 5: Verify green**

Run:

```bash
uv run pytest packages/simulation/tests/test_planning_returns.py -v
uv run pytest packages/simulation -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/simulation/simulation/planning_returns.py packages/simulation/tests/test_planning_returns.py
git commit -m "feat(simulation): retain planning return provenance"
```

---

### Task 5: Attach required resolved assumptions to public simulation results

**Files:**
- Modify: `packages/simulation/simulation/result.py`
- Modify: `packages/simulation/simulation/preprocess.py`
- Modify: `packages/simulation/simulation/aggregate.py`
- Modify: `packages/simulation/simulation/stub.py`
- Modify: `packages/simulation/simulation/__init__.py`
- Create: `packages/simulation/tests/test_resolved_assumptions.py`
- Modify: `packages/simulation/tests/test_aggregate.py`
- Modify: `packages/simulation/tests/test_result.py`
- Modify: `packages/simulation/tests/test_run_simulation.py`
- Modify: `packages/simulation/tests/test_engine.py`
- Modify: `packages/web/tests/test_simulation_cache.py`
- Modify: `packages/web/tests/test_charts.py`
- Modify: `packages/web/tests/test_spending_summary.py`

**Interfaces:**
- Produces:

```python
class ResolvedAssumptions(BaseModel):
    annual_inflation: float
    annual_stock_return: float
    annual_bond_return: float
    annual_stock_log_variance: float
    planning_preset: PlanningPreset
    inflation_source: Literal["manual", "live", "cache", "vendored"]
    inflation_observation_date: date | None = None
    sp500_source: MarketDataSource | None = None
    sp500_observation_date: date | None = None
    treasury_source: MarketDataSource | None = None
    treasury_observation_date: date | None = None
```

- Produces:

```python
def build_resolved_assumptions(
    *,
    inflation: InflationResolved,
    planning: PlanningReturns,
    preset: PlanningPreset,
) -> ResolvedAssumptions:
```

- Changes: `SimulationResult.resolved_assumptions` is required.
- Changes: `build_public_result(raw: RawSimulationResult, *, percentiles: list[int], composition: WealthBySource, start_month: tuple[int, int], resolved_assumptions: ResolvedAssumptions) -> SimulationResult`.

- [ ] **Step 1: Write snapshot assembly tests**

Create `test_resolved_assumptions.py`:

```python
def test_snapshot_uses_exact_resolver_values() -> None:
    annual_inflation = 0.023
    annual_stocks = 0.051
    annual_bonds = 0.018
    annual_variance = 0.031
    preset: PlanningPreset = "fixed"
    inflation = InflationResolved(
        annual=annual_inflation,
        monthly=annual_to_monthly(annual_inflation),
        source="manual",
    )
    planning = PlanningReturns(
        annual_stocks=annual_stocks,
        annual_bonds=annual_bonds,
        annual_stock_log_variance=annual_variance,
    )

    snapshot = build_resolved_assumptions(
        inflation=inflation, planning=planning, preset=preset
    )

    assert snapshot.annual_inflation == annual_inflation
    assert snapshot.annual_stock_return == annual_stocks
    assert snapshot.annual_bond_return == annual_bonds
    assert snapshot.annual_stock_log_variance == annual_variance
    assert snapshot.planning_preset == preset
    assert snapshot.inflation_source == "manual"


def test_snapshot_carries_only_present_market_provenance() -> None:
    sp500_date = date(2026, 5, 1)
    treasury_date = date(2026, 5, 2)
    sp500 = SP500Resolved(
        close=6_000.0, observation_date=sp500_date, source="live"
    )
    treasury = TreasuryYieldsResolved(
        yields={TWENTY_YEAR_TENOR: 0.018},
        observation_date=treasury_date,
        source="cache",
    )
    inflation = InflationResolved(
        annual=0.023,
        monthly=annual_to_monthly(0.023),
        source="suggested",
        market_source="vendored",
        observation_date=date(2026, 4, 30),
    )
    planning = PlanningReturns(
        annual_stocks=0.051,
        annual_bonds=0.018,
        annual_stock_log_variance=0.031,
        sp500=sp500,
        treasury=treasury,
    )

    snapshot = build_resolved_assumptions(
        inflation=inflation,
        planning=planning,
        preset="regression_prediction",
    )

    assert snapshot.sp500_source == sp500.source
    assert snapshot.sp500_observation_date == sp500_date
    assert snapshot.treasury_source == treasury.source
    assert snapshot.treasury_observation_date == treasury_date
```

- [ ] **Step 2: Add minimal scaffolding**

Define `ResolvedAssumptions` with the exact fields in Interfaces and add:

```python
def build_resolved_assumptions(
    *,
    inflation: InflationResolved,
    planning: PlanningReturns,
    preset: PlanningPreset,
) -> ResolvedAssumptions:
    raise NotImplementedError
```

Export `ResolvedAssumptions` from `simulation.__init__`.

- [ ] **Step 3: Run snapshot tests and confirm logical red**

Run:

```bash
uv run pytest packages/simulation/tests/test_resolved_assumptions.py -v
```

Expected: FAIL with `NotImplementedError`, not import or attribute failure.

- [ ] **Step 4: Implement snapshot assembly**

```python
def build_resolved_assumptions(
    *,
    inflation: InflationResolved,
    planning: PlanningReturns,
    preset: PlanningPreset,
) -> ResolvedAssumptions:
    inflation_source = (
        "manual" if inflation.source == "manual" else inflation.market_source
    )
    if inflation_source is None:
        raise ValueError("suggested inflation is missing market provenance")
    return ResolvedAssumptions(
        annual_inflation=inflation.annual,
        annual_stock_return=planning.annual_stocks,
        annual_bond_return=planning.annual_bonds,
        annual_stock_log_variance=planning.annual_stock_log_variance,
        planning_preset=preset,
        inflation_source=inflation_source,
        inflation_observation_date=inflation.observation_date,
        sp500_source=planning.sp500.source if planning.sp500 else None,
        sp500_observation_date=(
            planning.sp500.observation_date if planning.sp500 else None
        ),
        treasury_source=planning.treasury.source if planning.treasury else None,
        treasury_observation_date=(
            planning.treasury.observation_date if planning.treasury else None
        ),
    )
```

- [ ] **Step 5: Write pipeline pass-through tests**

Add one behavior per test:

```python
def _resolved_assumptions() -> ResolvedAssumptions:
    return ResolvedAssumptions(
        annual_inflation=0.02,
        annual_stock_return=0.05,
        annual_bond_return=0.02,
        annual_stock_log_variance=0.03,
        planning_preset="fixed",
        inflation_source="manual",
    )


def _composition() -> WealthBySource:
    zeros = np.zeros(_MONTHS, dtype=np.float64)
    return WealthBySource(
        job=zeros.copy(),
        social_security=zeros.copy(),
        pension=zeros.copy(),
        manual=zeros.copy(),
    )


def test_build_public_result_carries_resolved_assumptions() -> None:
    assumptions = _resolved_assumptions()
    result = build_public_result(
        _raw(),
        percentiles=list(DEFAULT_PERCENTILES),
        composition=_composition(),
        start_month=(2026, 1),
        resolved_assumptions=assumptions,
    )
    assert result.resolved_assumptions == assumptions
```

In `test_run_simulation.py`, configure a Fixed preset from bound expected values and assert `result.resolved_assumptions` matches those values. In `test_result.py`, copy a result with one changed assumptions value and assert the results are unequal.

- [ ] **Step 6: Add pipeline scaffolding and confirm logical red**

Add required `inflation_resolved: InflationResolved` and `planning_resolved: PlanningReturns` fields to `ProcessedPlan`, populate them with the existing resolver outputs in `preprocess`, add required `resolved_assumptions` to `SimulationResult`, and add the keyword to `build_public_result`. Temporarily pass this exact wrong-value scaffold from `run_simulation` so constructors succeed while value assertions remain logically red:

```python
resolved_assumptions = ResolvedAssumptions(
    annual_inflation=0.0,
    annual_stock_return=0.0,
    annual_bond_return=0.0,
    annual_stock_log_variance=0.0,
    planning_preset=plan.planning_returns.preset,
    inflation_source="manual",
)
```

Update every manual `ProcessedPlan(...)` and `SimulationResult(...)` constructor listed in Files with a shared valid `_resolved_assumptions()` or resolver fixture. Do not make the production field optional just to avoid updating tests.

Run:

```bash
uv run pytest packages/simulation/tests/test_aggregate.py packages/simulation/tests/test_result.py packages/simulation/tests/test_run_simulation.py -v
```

Expected: logical value assertions fail; there must be no missing-argument or import failures.

- [ ] **Step 7: Wire the exact preprocessed resolver objects**

In the existing `ProcessedPlan(...)` return constructor, add `inflation_resolved=inflation` and `planning_resolved=planning`.

In `run_simulation`:

```python
resolved_assumptions = build_resolved_assumptions(
    inflation=processed.inflation_resolved,
    planning=processed.planning_resolved,
    preset=plan.planning_returns.preset,
)
return build_public_result(
    raw,
    percentiles=resolved,
    composition=composition,
    start_month=(today.year, today.month),
    resolved_assumptions=resolved_assumptions,
)
```

In `build_public_result`, assign the required field directly. Do not call either resolver a second time.

- [ ] **Step 8: Verify green and compatibility**

Run:

```bash
uv run pytest packages/simulation/tests/test_resolved_assumptions.py packages/simulation/tests/test_aggregate.py packages/simulation/tests/test_result.py packages/simulation/tests/test_run_simulation.py packages/simulation/tests/test_engine.py -v
uv run pytest packages/simulation packages/web/tests/test_simulation_cache.py packages/web/tests/test_charts.py packages/web/tests/test_spending_summary.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/simulation/simulation/result.py packages/simulation/simulation/preprocess.py packages/simulation/simulation/aggregate.py packages/simulation/simulation/stub.py packages/simulation/simulation/__init__.py packages/simulation/tests packages/web/tests/test_simulation_cache.py packages/web/tests/test_charts.py packages/web/tests/test_spending_summary.py
git commit -m "feat(simulation): expose resolved assumptions on results"
```

---

### Task 6: Add the Spending goals editor and generic list reminting

**Files:**
- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/routes.py`
- Modify: `packages/web/web/sections.py`
- Modify: `packages/web/web/app.py`
- Create: `packages/web/web/templates/editor_spending.html`
- Modify: `packages/web/web/templates/index.html`
- Modify: `packages/web/web/static/editor_lists.js`
- Create: `packages/web/tests/test_spending_editor.py`

**Interfaces:**
- Produces route constants `EDITOR_SPENDING = "/editor/spending"` and `PLAN_SPENDING = "/plan/spending"`.
- Produces section title `SPENDING_GOALS_TITLE = "Spending goals"`.
- Produces field constants:

```python
ESSENTIAL_PREFIX = "essential"
DISCRETIONARY_PREFIX = "discretionary"
LEGACY_TARGET = "legacy_target"
LEGACY_TARGET_HELP = "Target at the plan horizon, in today's dollars."
STREAM_LABEL = "label"
STREAM_MONTHLY_AMOUNT = "monthly_amount"
STREAM_IS_NOMINAL = "is_nominal"
STREAM_ANNUAL_GROWTH_RATE = "annual_growth_rate"
STREAM_START = "start"
STREAM_END = "end"
```

- Produces `SpendingGoalsForm.from_form(form: FormData, *, today: date, existing_essential: list[TimedStream], existing_discretionary: list[TimedStream], existing_legacy_target: Decimal) -> SpendingGoalsForm` and `apply_to(plan: Plan) -> Plan`.

- [ ] **Step 1: Write spending form and route tests**

Create `test_spending_editor.py` with one behavior per test. The first group must include:

```python
def _stream_data(*, prefix: str, label: str, amount: str) -> dict[str, str]:
    return {
        f"{prefix}[0].label": label,
        f"{prefix}[0].monthly_amount": amount,
        f"{prefix}[0].annual_growth_rate": "0%",
        f"{prefix}[0].start_kind": boundaries.KIND_NOW,
        f"{prefix}[0].end_kind": boundaries.KIND_NONE,
    }


def test_patch_spending_keeps_categories_separate(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    essential_label = "Healthcare"
    discretionary_label = "Travel"
    essential_amount = "700"
    discretionary_amount = "500"
    legacy_target = "100000"
    data = {
        **_stream_data(
            prefix=forms.ESSENTIAL_PREFIX,
            label=essential_label,
            amount=essential_amount,
        ),
        **_stream_data(
            prefix=forms.DISCRETIONARY_PREFIX,
            label=discretionary_label,
            amount=discretionary_amount,
        ),
        forms.LEGACY_TARGET: legacy_target,
    }

    response = client.patch(f"{PLAN_SPENDING}?plan={plan_id}", data=data)

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert [stream.label for stream in saved.extra_essential_spending] == [
        essential_label
    ]
    assert [stream.label for stream in saved.extra_discretionary_spending] == [
        discretionary_label
    ]
    assert saved.legacy_target == Decimal(legacy_target)
```

Add separate tests for:

- an `is_nominal` checkbox setting only that row's flag;
- an empty submission clearing both lists and setting the submitted legacy value;
- invalid amount returning 422 without changing either list or legacy;
- existing cent amounts surviving a formatted USD echo via `EXISTING_INDEX`;
- sparse numeric indexes preserving numeric order;
- unrelated `risk` and `sampling` objects remaining equal after PATCH;
- GET rendering `SPENDING_GOALS_TITLE`, `LEGACY_TARGET_HELP`, Now on starts, max-age only on ends, and Plan horizon on ends.

Bind all expected labels, amounts, and prior objects once; do not repeat arrange literals in assertions.

- [ ] **Step 2: Add structural scaffolding**

Add route/title/field constants. Add:

```python
class SpendingGoalsForm:
    def __init__(
        self,
        *,
        essential: list[TimedStream],
        discretionary: list[TimedStream],
        legacy_target: Decimal,
    ) -> None:
        self.essential = essential
        self.discretionary = discretionary
        self.legacy_target = legacy_target

    @classmethod
    def from_form(
        cls,
        form: FormData,
        *,
        today: date,
        existing_essential: list[TimedStream],
        existing_discretionary: list[TimedStream],
        existing_legacy_target: Decimal,
    ) -> SpendingGoalsForm:
        raise NotImplementedError

    def apply_to(self, plan: Plan) -> Plan:
        raise NotImplementedError
```

Register GET/PATCH handlers that reach the scaffold and create a minimal `editor_spending.html` containing the title and empty form. This removes import/route/template structural errors before red.

- [ ] **Step 3: Run the route tests and confirm logical red**

Run:

```bash
uv run pytest packages/web/tests/test_spending_editor.py -v
```

Expected: PATCH tests fail with `NotImplementedError`; GET detail assertions fail on missing controls. No 404, template-not-found, import, or attribute failure is acceptable.

- [ ] **Step 4: Implement reusable list parsing and merge**

Refactor `_stream_from_row` to use the exported suffix constants. Add:

```python
def _streams_from_form(
    form: FormData,
    *,
    prefix: str,
    today: date,
    existing: list[TimedStream],
) -> list[TimedStream]:
    rows = boundaries.collect_indexed_rows(form, prefix)
    streams: list[TimedStream] = []
    claimed: set[int] = set()
    for row in rows:
        previous = _resolve_previous(
            row,
            existing=existing,
            claimed=claimed,
            amount_of=lambda stream: stream.monthly_amount,
            amount_field=STREAM_MONTHLY_AMOUNT,
        )
        streams.append(_stream_from_row(row, today=today, previous=previous))
    return streams
```

`SpendingGoalsForm.from_form` calls the helper separately for each prefix. Parse legacy safely:

```python
raw_legacy = form.get(LEGACY_TARGET, "")
if not isinstance(raw_legacy, str):
    raise ValueError("Legacy target must be text")
legacy_target = parse_usd(raw_legacy, previous=existing_legacy_target)
```

Implement merge:

```python
def apply_to(self, plan: Plan) -> Plan:
    return plan.model_copy(
        update={
            "extra_essential_spending": self.essential,
            "extra_discretionary_spending": self.discretionary,
            "legacy_target": self.legacy_target,
        }
    )
```

The async PATCH handler passes the existing two lists and legacy value, catches `(ValidationError, ValueError, ArithmeticError)`, saves on success, and returns status 200.

- [ ] **Step 5: Build the complete spending template**

Use one macro inside `editor_spending.html`:

```html
{% import "_boundary.html" as boundary %}
{% set people = forms.people_choices(plan) %}

{% macro stream_row(prefix, index, stream, choices) %}
<fieldset class="row stream-row">
  <button type="button" data-remove-row>Remove</button>
  {% if stream %}
  <input type="hidden" name="{{ prefix }}[{{ index }}].{{ forms.EXISTING_INDEX }}" value="{{ index }}">
  {% endif %}
  <label>Label <input type="text" name="{{ prefix }}[{{ index }}].{{ forms.STREAM_LABEL }}" value="{{ (stream.label or '') if stream else '' }}"></label>
  <label>Monthly amount <input type="text" inputmode="decimal" class="currency-input" name="{{ prefix }}[{{ index }}].{{ forms.STREAM_MONTHLY_AMOUNT }}" value="{{ (stream.monthly_amount if stream else 0)|usd }}"></label>
  <label class="checkbox-label"><input type="checkbox" name="{{ prefix }}[{{ index }}].{{ forms.STREAM_IS_NOMINAL }}" value="on"{% if stream and stream.is_nominal %} checked{% endif %}> Nominal (not inflation-adjusted)</label>
  <label>Annual growth <input type="text" inputmode="decimal" class="percent-input" name="{{ prefix }}[{{ index }}].{{ forms.STREAM_ANNUAL_GROWTH_RATE }}" value="{{ (stream.annual_growth_rate if stream else 0)|percent }}"></label>
  <div class="boundary-field">Start {{ boundary.boundary_control(prefix ~ "[" ~ index ~ "]." ~ forms.STREAM_START, boundaries.to_form(stream.start) if stream else {"kind": boundaries.KIND_NOW}, choices, allow_now=True) }}</div>
  <div class="boundary-field">End {{ boundary.boundary_control(prefix ~ "[" ~ index ~ "]." ~ forms.STREAM_END, boundaries.to_form(stream.end) if stream else {"kind": boundaries.KIND_NONE}, choices, allow_now=True, allow_none=True, allow_max_age=True, none_label="Plan horizon") }}</div>
</fieldset>
{% endmacro %}
```

Render two `.rows[data-prefix]` containers, each with current rows, a `<template class="row-template">`, and its category-specific Add button. Add the legacy field using `forms.LEGACY_TARGET` and help copy using `forms.LEGACY_TARGET_HELP`. The enclosing form PATCHes `routes.PLAN_SPENDING` with the standard 750ms input/change debounce and `hx-swap="none"`.

Include it in `index.html` after Manual income and before Risk.

- [ ] **Step 6: Generalize row reminting**

In `editor_lists.js`, replace the hardcoded selector array with:

```javascript
form
  .querySelectorAll(".rows[data-prefix] > .row")
  .forEach(function (row, position) {
    const container = row.parentElement;
    const prefix = container.dataset.prefix;
    // retain the existing wire-index and hidden existing_index logic
  });
```

Do not renumber wire indexes on remove; continue reminting only `existing_index` after successful saves.

- [ ] **Step 7: Verify green**

Run:

```bash
uv run pytest packages/web/tests/test_spending_editor.py packages/web/tests/test_manual_income_editor.py packages/web/tests/test_jobs_editor.py -v
uv run pytest packages/web -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/web/web/forms.py packages/web/web/routes.py packages/web/web/sections.py packages/web/web/app.py packages/web/web/templates/editor_spending.html packages/web/web/templates/index.html packages/web/web/static/editor_lists.js packages/web/tests/test_spending_editor.py
git commit -m "feat(web): add spending goals editor"
```

---

### Task 7: Add the progressive Risk editor

**Files:**
- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/routes.py`
- Modify: `packages/web/web/sections.py`
- Modify: `packages/web/web/app.py`
- Create: `packages/web/web/templates/editor_risk.html`
- Modify: `packages/web/web/templates/index.html`
- Create: `packages/web/tests/test_risk_editor.py`

**Interfaces:**
- Produces `EDITOR_RISK`, `PLAN_RISK`, and `RISK_TITLE = "Risk"`.
- Produces `RiskForm` with all five `RiskConfig` fields and `apply_to(plan)`.
- Visible fields: risk tolerance and additional spending tilt. Advanced disclosure: age delta, legacy delta, and time preference.

- [ ] **Step 1: Write route, merge, and rendering tests**

Add:

```python
def test_patch_risk_round_trips_visible_fields(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    tolerance = Decimal("14")
    tilt = Decimal("0.01")

    response = client.patch(
        f"{PLAN_RISK}?plan={plan_id}",
        data={
            forms.RISK_TOLERANCE_AT_20: str(tolerance),
            forms.ADDITIONAL_ANNUAL_SPENDING_TILT: format_percent(tilt),
            forms.DELTA_AT_MAX_AGE: "0",
            forms.LEGACY_DELTA_FROM_AT_20: "0",
            forms.TIME_PREFERENCE: "0%",
        },
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk.risk_tolerance_at_20 == tolerance
    assert saved.risk.additional_annual_spending_tilt == tilt
```

Add separate tests for advanced fields, negative tolerance returning 422 without persistence, unrelated spending/sampling preservation, GET title, slider bounds derived from `RISK_TOLERANCE_NUM_VALUES`, and `<details>` containing all advanced field names.

- [ ] **Step 2: Add scaffold and run logical red**

Add route/title/field constants and:

```python
class RiskForm(BaseModel):
    risk_tolerance_at_20: Decimal
    delta_at_max_age: Decimal
    legacy_delta_from_at_20: Decimal
    time_preference: Decimal
    additional_annual_spending_tilt: Decimal

    def apply_to(self, plan: Plan) -> Plan:
        raise NotImplementedError
```

Register GET/PATCH routes and a minimal template. Run:

```bash
uv run pytest packages/web/tests/test_risk_editor.py -v
```

Expected: PATCH tests fail with `NotImplementedError`; GET detail assertions fail logically. Resolve any structural failure before proceeding.

- [ ] **Step 3: Implement DTO, handler, and full template**

Build `RiskConfig` in `apply_to`:

```python
def apply_to(self, plan: Plan) -> Plan:
    risk = RiskConfig.model_validate(self.model_dump())
    return plan.model_copy(update={"risk": risk})
```

The handler parses `risk_tolerance_at_20`, `delta_at_max_age`, and `legacy_delta_from_at_20` as raw `Decimal` tolerance points. It parses only `time_preference` and `additional_annual_spending_tilt` with `parse_percent`. It catches the standard exception tuple and saves only on success.

The template:

- uses a range input with `min="0"`, `max="{{ forms.RISK_TOLERANCE_NUM_VALUES - 1 }}"`, and `step="1"`;
- renders Conservative, Moderate, and Aggressive text without duplicating the RRA constants;
- shows spending tilt outside disclosure;
- wraps `DELTA_AT_MAX_AGE` and `LEGACY_DELTA_FROM_AT_20` as numeric tolerance-point inputs plus percent-formatted `TIME_PREFERENCE` in `<details><summary>Advanced risk settings</summary>`;
- PATCHes with the standard debounce.

- [ ] **Step 4: Verify green**

Run:

```bash
uv run pytest packages/web/tests/test_risk_editor.py -v
uv run pytest packages/web -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/forms.py packages/web/web/routes.py packages/web/web/sections.py packages/web/web/app.py packages/web/web/templates/editor_risk.html packages/web/web/templates/index.html packages/web/tests/test_risk_editor.py
git commit -m "feat(web): add progressive risk editor"
```

---

### Task 8: Add Market assumptions with all return presets

**Files:**
- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/routes.py`
- Modify: `packages/web/web/sections.py`
- Modify: `packages/web/web/app.py`
- Create: `packages/web/web/templates/editor_market_assumptions.html`
- Create: `packages/web/web/static/editor_conditional.js`
- Modify: `packages/web/web/templates/index.html`
- Create: `packages/web/tests/test_market_assumptions_editor.py`

**Interfaces:**
- Produces `EDITOR_MARKET_ASSUMPTIONS`, `PLAN_MARKET_ASSUMPTIONS`, and title.
- Produces UI constants:

```python
FIXED_EQUITY_PREMIUM_FORM_DEFAULT = Decimal("0.03")
CUSTOM_STOCKS_BASE_FORM_DEFAULT: StockPresetBase = "regression_prediction"
CUSTOM_BONDS_BASE_FORM_DEFAULT: BondPresetBase = "twenty_year_tips_yield"
```

- Produces `MarketAssumptionsForm`, which merges only `inflation` and `planning_returns`, preserving omitted inactive values.
- Produces `editor_conditional.js`, which updates visibility, disabled state, and required state before HTMX sees a bubbled change event.

- [ ] **Step 1: Write inflation and preset behavior tests**

Add a parametrized happy-path test covering every value from `get_args(PlanningPreset)`; supply required fields only for Fixed equity premium, Custom, and Fixed. Assert the saved preset equals the parameter.

Add focused tests:

```python
def _market_form_data(
    *,
    inflation_mode: str = "suggested",
    planning_preset: str = "regression_prediction",
) -> dict[str, str]:
    return {
        forms.INFLATION_MODE: inflation_mode,
        forms.PLANNING_PRESET: planning_preset,
        forms.STOCK_VOLATILITY_SCALE: "1",
    }


def test_switching_to_suggested_preserves_manual_inflation_rate(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stored_manual_rate = Decimal("0.027")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.inflation = InflationConfig(
        mode="manual", manual_annual_rate=stored_manual_rate
    )
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data=_market_form_data(inflation_mode="suggested"),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.inflation.mode == "suggested"
    assert saved.inflation.manual_annual_rate == stored_manual_rate
```

Add one behavior per test for Manual rate round-trip, Manual without rate returning 422, Fixed premium without premium returning 422, Custom without both bases returning 422, inactive Custom values preserved after switching presets, stock volatility scale round-trip, unrelated sampling preservation, GET rendering all values from `get_args(PlanningPreset)`, and conditional data hooks/default values.

- [ ] **Step 2: Add form and route scaffolding**

Add literals/labels derived from `get_args`, field constants, defaults, and:

```python
class MarketAssumptionsForm(BaseModel):
    inflation_mode: Literal["suggested", "manual"]
    inflation_manual_annual_rate: Decimal | None = None
    planning_preset: PlanningPreset
    fixed_equity_premium: Decimal | None = None
    custom_stocks_base: StockPresetBase | None = None
    custom_bonds_base: BondPresetBase | None = None
    custom_stocks_delta: Decimal | None = None
    custom_bonds_delta: Decimal | None = None
    expected_annual_return_stocks: Decimal | None = None
    expected_annual_return_bonds: Decimal | None = None
    stock_volatility_scale: Decimal | None = None

    def apply_to(self, plan: Plan) -> Plan:
        raise NotImplementedError
```

Register GET/PATCH and minimal template. The GET must load settings and call `_load_simulation` through the cache so a direct section GET can render current assumptions later.

- [ ] **Step 3: Run and confirm logical red**

Run:

```bash
uv run pytest packages/web/tests/test_market_assumptions_editor.py -v
```

Expected: PATCH tests reach `NotImplementedError`; GET option/hook assertions fail logically. No import, route, or template failure is acceptable.

- [ ] **Step 4: Implement preservation-aware merge**

Use:

```python
def apply_to(self, plan: Plan) -> Plan:
    inflation_data = plan.inflation.model_dump()
    inflation_data["mode"] = self.inflation_mode
    if self.inflation_manual_annual_rate is not None:
        inflation_data["manual_annual_rate"] = self.inflation_manual_annual_rate

    returns_data = plan.planning_returns.model_dump()
    returns_data["preset"] = self.planning_preset
    for field in (
        "fixed_equity_premium",
        "custom_stocks_base",
        "custom_bonds_base",
        "custom_stocks_delta",
        "custom_bonds_delta",
        "expected_annual_return_stocks",
        "expected_annual_return_bonds",
        "stock_volatility_scale",
    ):
        value = getattr(self, field)
        if value is not None:
            returns_data[field] = value

    return plan.model_copy(
        update={
            "inflation": InflationConfig.model_validate(inflation_data),
            "planning_returns": PlanningReturnsConfig.model_validate(
                returns_data
            ),
        }
    )
```

The PATCH handler parses optional rates with `parse_optional_percent`, parses optional scale as `Decimal`, validates literal selector values through the DTO/core models, and catches the standard exception tuple.

- [ ] **Step 5: Implement complete conditional template**

The form contains:

- Inflation selector and manual group with `data-condition-value="manual"`.
- Planning selector with all `PLANNING_PRESET_LABELS`.
- Fixed premium group using the stored value or `FIXED_EQUITY_PREMIUM_FORM_DEFAULT`.
- Custom group with stock/bond base selectors and delta inputs using stored values or named form defaults.
- Fixed group using stored expected returns (which already have core defaults).
- Always-available stock volatility scale inside `<details><summary>Customize</summary>`.
- A stable, initially empty `<div id="resolved-assumptions-summary"></div>` container; Task 10 adds the shared partial.

Each conditional input uses:

```html
data-condition-input
data-required-when-active
```

and its wrapper uses:

```html
data-condition-group
data-condition-controller-id="planning-preset"
data-condition-value="custom"
```

- [ ] **Step 6: Implement conditional JavaScript**

Create:

```javascript
(function () {
  function syncController(controller) {
    const form = controller.closest("form");
    const controllerId = controller.dataset.conditionController;
    form
      .querySelectorAll(
        "[data-condition-group][data-condition-controller-id='" +
          controllerId +
          "']"
      )
      .forEach(function (group) {
        const values = (group.dataset.conditionValue || "").split(" ");
        const active = values.indexOf(controller.value) !== -1;
        group.hidden = !active;
        group.querySelectorAll("[data-condition-input]").forEach(function (input) {
          input.disabled = !active;
          input.required =
            active && input.hasAttribute("data-required-when-active");
        });
      });
  }

  function initConditionalFields(root) {
    root.querySelectorAll("[data-condition-controller]").forEach(function (controller) {
      if (!controller.dataset.conditionBound) {
        controller.addEventListener("change", function () {
          syncController(controller);
        });
        controller.dataset.conditionBound = "true";
      }
      syncController(controller);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initConditionalFields(document);
  });
  document.body.addEventListener("htmx:afterSettle", function (event) {
    initConditionalFields(event.detail.target || document);
  });
})();
```

Load it after `editor_lists.js` in `index.html`. Direct listeners run before the change event bubbles to HTMX, so required/disabled state reflects the newly selected mode.

- [ ] **Step 7: Verify green**

Run:

```bash
uv run pytest packages/web/tests/test_market_assumptions_editor.py -v
uv run pytest packages/web -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/web/web/forms.py packages/web/web/routes.py packages/web/web/sections.py packages/web/web/app.py packages/web/web/templates/editor_market_assumptions.html packages/web/web/static/editor_conditional.js packages/web/web/templates/index.html packages/web/tests/test_market_assumptions_editor.py
git commit -m "feat(web): add market assumptions editor"
```

---

### Task 9: Add collapsed Simulation details editor

**Files:**
- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/routes.py`
- Modify: `packages/web/web/sections.py`
- Modify: `packages/web/web/app.py`
- Create: `packages/web/web/templates/editor_simulation_details.html`
- Modify: `packages/web/web/templates/index.html`
- Create: `packages/web/tests/test_simulation_details_editor.py`

**Interfaces:**
- Produces `parse_percentiles_field(raw: str) -> list[int]`, delegating contract validation to `core.models.normalize_percentiles`.
- Produces `SimulationDetailsForm` owning `sampling` and `advanced`.
- Produces help text:

```python
PERCENTILES_WEALTH_MAPPING_HELP = (
    "Wealth composition Low, Middle, and High use the first, middle, "
    "and last configured percentiles."
)
```

- [ ] **Step 1: Write parser, PATCH, merge, and render tests**

Add:

```python
def test_patch_simulation_details_updates_sampling_and_sorts_percentiles(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    block_size = 48
    num_runs = 300
    seed = 9_876
    submitted_percentiles = [95, 5, 50]
    expected_percentiles = sorted(submitted_percentiles)

    response = client.patch(
        f"{PLAN_SIMULATION_DETAILS}?plan={plan_id}",
        data={
            forms.BLOCK_SIZE_MONTHS: str(block_size),
            forms.NUM_RUNS: str(num_runs),
            forms.STAGGER_RUN_STARTS: "on",
            forms.SAMPLING_SEED: str(seed),
            forms.PERCENTILES: ", ".join(
                str(value) for value in submitted_percentiles
            ),
        },
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.sampling.block_size_months == block_size
    assert saved.sampling.num_runs == num_runs
    assert saved.sampling.stagger_run_starts is True
    assert saved.sampling.seed == seed
    assert saved.advanced.percentiles == expected_percentiles
```

Add separate tests for unchecked stagger, duplicate/empty/out-of-range/malformed percentile input returning 422 without save, unrelated risk preservation, GET collapsed by default (no `open` attribute), all four sampling names, and mapping help.

- [ ] **Step 2: Add scaffold and confirm logical red**

Add constants and:

```python
def parse_percentiles_field(raw: str) -> list[int]:
    raise NotImplementedError


class SimulationDetailsForm(BaseModel):
    block_size_months: int
    num_runs: int
    stagger_run_starts: bool
    seed: int
    percentiles: list[int]

    def apply_to(self, plan: Plan) -> Plan:
        raise NotImplementedError
```

Register routes and minimal template. Run:

```bash
uv run pytest packages/web/tests/test_simulation_details_editor.py -v
```

Expected: parser/PATCH tests fail with `NotImplementedError`; GET detail tests fail logically. Resolve structural failures first.

- [ ] **Step 3: Implement parser and merge**

```python
def parse_percentiles_field(raw: str) -> list[int]:
    tokens = [token.strip() for token in raw.split(",")]
    if not tokens or any(not token for token in tokens):
        raise ValueError("Enter one or more comma-separated percentiles")
    try:
        parsed = [int(token) for token in tokens]
    except ValueError as exc:
        raise ValueError("Percentiles must be whole numbers") from exc
    return normalize_percentiles(parsed)


def apply_to(self, plan: Plan) -> Plan:
    sampling = SamplingConfig(
        block_size_months=self.block_size_months,
        num_runs=self.num_runs,
        stagger_run_starts=self.stagger_run_starts,
        seed=self.seed,
    )
    advanced = AdvancedConfig(percentiles=self.percentiles)
    return plan.model_copy(
        update={"sampling": sampling, "advanced": advanced}
    )
```

The handler parses percentiles before DTO construction, catches the standard exception tuple, and saves only on success.

- [ ] **Step 4: Implement collapsed template**

Use:

```html
<details class="editor-section">
  <summary><h2>{{ sections.SIMULATION_DETAILS_TITLE }}</h2></summary>
  <form
    hx-patch="{{ routes.PLAN_SIMULATION_DETAILS }}?plan={{ plan_id }}"
    hx-trigger="input changed delay:750ms, change delay:750ms"
    hx-swap="none"
  >
    <label>Block size (months)
      <input type="number" min="1" name="{{ forms.BLOCK_SIZE_MONTHS }}" value="{{ plan.sampling.block_size_months }}">
    </label>
    <label>Number of runs
      <input type="number" min="1" name="{{ forms.NUM_RUNS }}" value="{{ plan.sampling.num_runs }}">
    </label>
    <label class="checkbox-label">
      <input type="checkbox" name="{{ forms.STAGGER_RUN_STARTS }}" value="on"{% if plan.sampling.stagger_run_starts %} checked{% endif %}>
      Stagger run starts
    </label>
    <label>Sampling seed
      <input type="number" name="{{ forms.SAMPLING_SEED }}" value="{{ plan.sampling.seed }}">
    </label>
    <label>Output percentiles
      <input type="text" name="{{ forms.PERCENTILES }}" value="{{ plan.advanced.percentiles|join(', ') }}">
    </label>
    <p>{{ forms.PERCENTILES_WEALTH_MAPPING_HELP }}</p>
  </form>
</details>
```

Do not add `open`; include after Market assumptions and before Portfolio.

- [ ] **Step 5: Verify green**

Run:

```bash
uv run pytest packages/web/tests/test_simulation_details_editor.py packages/core/tests/test_advanced_config.py -v
uv run pytest packages/web -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/web/web/forms.py packages/web/web/routes.py packages/web/web/sections.py packages/web/web/app.py packages/web/web/templates/editor_simulation_details.html packages/web/web/templates/index.html packages/web/tests/test_simulation_details_editor.py
git commit -m "feat(web): add simulation details editor"
```

---

### Task 10: Render and refresh resolved assumptions from the cached result

**Files:**
- Create: `packages/web/web/resolved_assumptions.py`
- Create: `packages/web/web/templates/_resolved_assumptions.html`
- Modify: `packages/web/web/templates/editor_market_assumptions.html`
- Modify: `packages/web/web/templates/results.html`
- Modify: `packages/web/web/app.py`
- Modify: `packages/web/AGENTS.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`
- Create: `packages/web/tests/test_resolved_assumptions_summary.py`

**Interfaces:**
- Produces:

```python
UNAVAILABLE_MESSAGE = "Unavailable for current settings"
SOURCE_LABELS = {
    "manual": "Manual",
    "live": "Live",
    "cache": "Cached",
    "vendored": "Vendored fallback",
}

def annual_stock_log_volatility(assumptions: ResolvedAssumptions) -> float:
    return math.sqrt(assumptions.annual_stock_log_variance)
```

- Stable OOB target: `#resolved-assumptions-summary`.
- Home and direct editor GET render the current cached result. `/results` adds the same summary partial with `hx-swap-oob="innerHTML"`.

- [ ] **Step 1: Write formatter and rendering tests**

Create tests:

```python
def _assumptions(
    *,
    annual_stock_log_variance: float,
) -> ResolvedAssumptions:
    return ResolvedAssumptions(
        annual_inflation=0.023,
        annual_stock_return=0.051,
        annual_bond_return=0.018,
        annual_stock_log_variance=annual_stock_log_variance,
        planning_preset="regression_prediction",
        inflation_source="vendored",
        inflation_observation_date=date(2026, 4, 30),
        sp500_source="cache",
        sp500_observation_date=date(2026, 5, 1),
        treasury_source="live",
        treasury_observation_date=date(2026, 5, 2),
    )


def test_stock_volatility_is_square_root_of_resolved_variance() -> None:
    annual_variance = 0.0324
    expected_volatility = math.sqrt(annual_variance)
    assumptions = _assumptions(annual_stock_log_variance=annual_variance)

    actual = annual_stock_log_volatility(assumptions)

    assert actual == pytest.approx(expected_volatility)
```

Add one behavior per test for:

- home success rendering annual inflation, stock return, bond return, volatility, preset label, source labels, and applicable dates;
- home simulation failure rendering `UNAVAILABLE_MESSAGE` without prior numeric values;
- `/results` success containing exactly one OOB target with current values;
- `/results` simulation failure containing the OOB target with `UNAVAILABLE_MESSAGE`;
- direct Market assumptions GET using the cache and rendering current assumptions;
- Fixed/Historical presets rendering explicit preset labels without fake S&P/Treasury dates.

Use the existing `monkeypatch.setattr(app_module, "run_simulation", stub)` pattern. Build `SimulationResult` from a shared test helper with a required `ResolvedAssumptions`; bind every expected value/date once.

- [ ] **Step 2: Add formatter and template scaffolding**

Create the module with constants and:

```python
def annual_stock_log_volatility(
    assumptions: ResolvedAssumptions,
) -> float:
    raise NotImplementedError
```

Register it as `templates.env.globals["resolved_assumptions"]`. Create `_resolved_assumptions.html` with only the unavailable paragraph; the stable wrappers live in `editor_market_assumptions.html` and `results.html` so the DOM never contains nested duplicate IDs. Add `assumptions_oob=False` to home context and `True` to results context. This makes tests run without missing template/context symbols.

- [ ] **Step 3: Run and confirm logical red**

Run:

```bash
uv run pytest packages/web/tests/test_resolved_assumptions_summary.py -v
```

Expected: formatter fails with `NotImplementedError`; success-render assertions fail on missing values, while unavailable scaffolding may pass. No template, import, or required-constructor failure is acceptable.

- [ ] **Step 4: Implement display helpers and shared partial**

Implement the square root exactly. Add `planning_preset_label` using `forms.PLANNING_PRESET_LABELS`; source labels come only from `SOURCE_LABELS`.

The partial renders:

```html
{% if assumptions %}
<dl class="resolved-assumptions">
  <dt>Inflation</dt><dd>{{ assumptions.annual_inflation|percent }}</dd>
  <dt>Stocks</dt><dd>{{ assumptions.annual_stock_return|percent }}</dd>
  <dt>Bonds</dt><dd>{{ assumptions.annual_bond_return|percent }}</dd>
  <dt>Stock volatility</dt><dd>{{ resolved_assumptions.annual_stock_log_volatility(assumptions)|percent }}</dd>
  <dt>Planning preset</dt><dd>{{ forms.PLANNING_PRESET_LABELS[assumptions.planning_preset] }}</dd>
</dl>
<p>Inflation source: {{ resolved_assumptions.SOURCE_LABELS[assumptions.inflation_source] }}{% if assumptions.inflation_observation_date %} · {{ assumptions.inflation_observation_date.isoformat() }}{% endif %}</p>
{% if assumptions.sp500_source %}
<p>S&amp;P 500 source: {{ resolved_assumptions.SOURCE_LABELS[assumptions.sp500_source] }} · {{ assumptions.sp500_observation_date.isoformat() }}</p>
{% endif %}
{% if assumptions.treasury_source %}
<p>Treasury source: {{ resolved_assumptions.SOURCE_LABELS[assumptions.treasury_source] }} · {{ assumptions.treasury_observation_date.isoformat() }}</p>
{% endif %}
{% else %}
<p class="resolved-assumptions-unavailable">{{ resolved_assumptions.UNAVAILABLE_MESSAGE }}</p>
{% endif %}
```

For inflation, always show its source label and show its date only when non-`None`. Show S&P/Treasury rows only when source is non-`None`, with observation dates alongside.

- [ ] **Step 5: Wire initial, direct GET, and OOB contexts**

Home context:

```python
"assumptions": (
    result.resolved_assumptions if result is not None else None
),
"assumptions_oob": False,
```

Direct Market assumptions GET calls `_load_simulation` with current settings and passes the same `assumptions` value.

Results context:

```python
"assumptions": (
    result.resolved_assumptions if result is not None else None
),
"assumptions_oob": True,
```

At the end of `results.html`:

```html
{% if assumptions_oob %}
<div id="resolved-assumptions-summary" hx-swap-oob="innerHTML">
  {% include "_resolved_assumptions.html" %}
</div>
{% endif %}
```

Inside Market assumptions:

```html
<div id="resolved-assumptions-summary">
  {% include "_resolved_assumptions.html" %}
</div>
```

Because the failure route sets `result=None`, the OOB response replaces stale values with unavailable copy.

- [ ] **Step 6: Verify all Phase 4d web behavior**

Run:

```bash
uv run pytest packages/web/tests/test_resolved_assumptions_summary.py packages/web/tests/test_spending_editor.py packages/web/tests/test_risk_editor.py packages/web/tests/test_market_assumptions_editor.py packages/web/tests/test_simulation_details_editor.py -v
uv run pytest packages/web -q
```

Expected: PASS.

- [ ] **Step 7: Update durable docs and phase status**

In `packages/web/AGENTS.md`, document:

- the four Phase 4d sections and owned plan fields;
- `editor_conditional.js` only controls visibility/required/disabled transport state;
- the required `SimulationResult.resolved_assumptions`;
- charts and summary share one cached simulation and `/results` refreshes the summary OOB;
- failed simulations replace the summary with unavailable state.

In the rebuild index, check every Phase 4d exit criterion, add the design and plan links, and change **Next step** to Phase 4e only after full verification.

- [ ] **Step 8: Run full verification**

Run:

```bash
make
```

Expected: ruff check, ruff format check, pyright, and all pytest suites PASS.

Then start the app against a temporary initialized DB and manually verify:

```bash
TEMP_DB="$(mktemp -t life-finances-phase4d.XXXXXX.db)"
LIFE_FINANCES_DB_PATH="$TEMP_DB" uv run python scripts/init_db.py
LIFE_FINANCES_DB_PATH="$TEMP_DB" uv run uvicorn web.app:app --host 127.0.0.1 --port 8000
```

1. add one essential and one discretionary stream;
2. switch Inflation Suggested → Manual, confirm no invalid save occurs before entering a rate;
3. select Fixed premium, Custom, and Fixed and verify only relevant fields show;
4. edit risk and simulation details;
5. confirm one successful save refreshes both chart and resolved summary;
6. confirm Simulation details is collapsed on reload;
7. remove a spending row and confirm the remaining cent amount persists.

Stop uvicorn with Ctrl-C, then remove only the temporary path printed by `echo "$TEMP_DB"`.

- [ ] **Step 9: Commit**

```bash
git add packages/web/web/resolved_assumptions.py packages/web/web/templates/_resolved_assumptions.html packages/web/web/templates/editor_market_assumptions.html packages/web/web/templates/results.html packages/web/web/app.py packages/web/AGENTS.md docs/superpowers/plans/2026-06-12-rebuild-index.md packages/web/tests/test_resolved_assumptions_summary.py
git commit -m "feat(web): show resolved simulation assumptions"
```

---

## Completion criteria

- All ten task commits are present and focused.
- Every new test was observed failing logically before implementation and then passing.
- Essential/discretionary spending and scalar legacy are editable.
- Real and nominal spending streams are converted independently.
- Risk, Inflation, all seven planning-return presets, Sampling, and arbitrary unique percentiles are editable.
- The resolved summary carries the exact assumptions and source metadata consumed by the simulation.
- Chart and summary updates share one cached simulation result; failures clear stale assumptions.
- Stream IDs remain deferred to Phase 4e.
- `make` passes.
