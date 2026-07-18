# Phase 4b — Core Charts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the results-panel stub with Plotly charts driven by the existing percentile-major `SimulationResult`, plus a chart-type selector that survives HTMX debounced refreshes.

**Architecture:** `web/charts.py` (new) turns a `SimulationResult` + chart-type string into a Plotly figure JSON dict (pure functions, unit-testable). `GET /results?plan={id}&chart={type}` resolves the chart type, runs the simulation, and renders `results.html` (new, replaces `results_stub.html`). Plotly.js loads once from CDN in `base.html`; a small shell script calls `Plotly.react` after first paint and after each `htmx:afterSwap` on `#results-panel`, and keeps the panel's `hx-get` chart param in sync so `planUpdated` refreshes preserve the selection.

**Tech Stack:** Python 3.14+, FastAPI, Jinja2, HTMX, Plotly (Python, figure JSON only), plotly.js (CDN), pytest, ruff, pyright.

**Spec:** [`docs/superpowers/specs/2026-07-15-phase-4b-core-charts-design.md`](../specs/2026-07-15-phase-4b-core-charts-design.md)

## Global Constraints

- Testing policy (root `AGENTS.md` §Testing policy) applies to every task:
  - TDD red-green: write the failing test, run it, confirm the failure is **logical** (`AssertionError` / `NotImplementedError`) not **structural** (`ImportError` / `AttributeError`); add minimal scaffolding first if the failure is structural; only then implement.
  - Never hardcode the same literal in both arrange/act and assert — bind to a variable and reference it in both.
  - Pull constants from source: import chart-type constants, the default chart, and percentile defaults from production code in tests; never copy the string literals.
  - Test **our logic**, not library behavior — do not test that Plotly or Pydantic works.
  - One logical behavior per test; name tests after behavior; keep arrange/act/assert distinct; inject `today` / `ran_at` for time-dependent logic.
- Package dependency direction: `web → simulation, core`. Do NOT add chart helpers to `simulation`. `simulation` / `tools` never import `web`.
- Never edit lockfiles by hand — add dependencies with `uv add`.
- Chart-type string values (verbatim from spec §4): `portfolio`, `spending-total`, `asset-allocation-savings-portfolio`, `wealth-composition-low`, `wealth-composition-mid`, `wealth-composition-high`.
- Default chart: `spending-total`. Missing/invalid `chart` → fall back to default (never blank the panel).
- After substantive changes run `make` from the repo root and confirm it passes before claiming a task complete.
- Run all commands from the repository root.

---

### Task 1: Chart-type constants and resolver

**Files:**
- Create: `packages/web/web/charts.py`
- Test: `packages/web/tests/test_charts.py`

**Interfaces:**
- Consumes: nothing (leaf module).
- Produces:
  - Module-level constants: `PORTFOLIO`, `SPENDING_TOTAL`, `ASSET_ALLOCATION_SAVINGS`, `WEALTH_COMPOSITION_LOW`, `WEALTH_COMPOSITION_MID`, `WEALTH_COMPOSITION_HIGH` (all `str`).
  - `DEFAULT_CHART: str` (== `SPENDING_TOTAL`).
  - `CHART_TYPES: tuple[str, ...]` — all six valid values in display order: `(PORTFOLIO, SPENDING_TOTAL, ASSET_ALLOCATION_SAVINGS, WEALTH_COMPOSITION_LOW, WEALTH_COMPOSITION_MID, WEALTH_COMPOSITION_HIGH)`.
  - `resolve_chart_type(raw: str | None) -> str` — returns `raw` if it is in `CHART_TYPES`, else `DEFAULT_CHART`.

- [ ] **Step 1: Write the failing tests**

```python
# packages/web/tests/test_charts.py
import pytest

from web import charts


def test_default_chart_is_spending_total():
    assert charts.DEFAULT_CHART == charts.SPENDING_TOTAL


def test_resolve_returns_input_when_valid():
    expected = charts.PORTFOLIO
    assert charts.resolve_chart_type(expected) == expected


@pytest.mark.parametrize("raw", [None, "", "not-a-chart"])
def test_resolve_falls_back_to_default_when_invalid(raw):
    assert charts.resolve_chart_type(raw) == charts.DEFAULT_CHART


def test_all_chart_types_resolve_to_themselves():
    for chart_type in charts.CHART_TYPES:
        assert charts.resolve_chart_type(chart_type) == chart_type
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_charts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'web.charts'` (structural). Add the scaffolding in Step 3 until the failure becomes logical, then implement.

- [ ] **Step 3: Write the implementation**

```python
# packages/web/web/charts.py
from __future__ import annotations

PORTFOLIO = "portfolio"
SPENDING_TOTAL = "spending-total"
ASSET_ALLOCATION_SAVINGS = "asset-allocation-savings-portfolio"
WEALTH_COMPOSITION_LOW = "wealth-composition-low"
WEALTH_COMPOSITION_MID = "wealth-composition-mid"
WEALTH_COMPOSITION_HIGH = "wealth-composition-high"

DEFAULT_CHART = SPENDING_TOTAL

CHART_TYPES: tuple[str, ...] = (
    PORTFOLIO,
    SPENDING_TOTAL,
    ASSET_ALLOCATION_SAVINGS,
    WEALTH_COMPOSITION_LOW,
    WEALTH_COMPOSITION_MID,
    WEALTH_COMPOSITION_HIGH,
)


def resolve_chart_type(raw: str | None) -> str:
    if raw in CHART_TYPES:
        return raw  # type: ignore[return-value]
    return DEFAULT_CHART
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_charts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/charts.py packages/web/tests/test_charts.py
git commit -m "feat(web): add chart-type constants and resolver"
```

---

### Task 2: X-axis month labels helper

**Files:**
- Modify: `packages/web/web/charts.py`
- Test: `packages/web/tests/test_charts.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `month_labels(start_month: tuple[int, int], horizon_months: int) -> list[str]` — returns `horizon_months` `"YYYY-MM"` strings starting at `start_month` `(year, month)` and incrementing one calendar month per index (rolls over December → January).

- [ ] **Step 1: Write the failing tests**

```python
# add to packages/web/tests/test_charts.py
def test_month_labels_length_matches_horizon():
    horizon = 5
    labels = charts.month_labels((2026, 1), horizon)
    assert len(labels) == horizon


def test_month_labels_start_and_year_rollover():
    start_year, start_month = 2026, 11
    labels = charts.month_labels((start_year, start_month), 3)
    assert labels == ["2026-11", "2026-12", "2027-01"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_charts.py -k month_labels -v`
Expected: FAIL — `AttributeError: module 'web.charts' has no attribute 'month_labels'` (structural). Add a stub `def month_labels(start_month, horizon_months): raise NotImplementedError` and re-run to confirm a logical failure before implementing.

- [ ] **Step 3: Write the implementation**

```python
# add to packages/web/web/charts.py
def month_labels(start_month: tuple[int, int], horizon_months: int) -> list[str]:
    year, month = start_month
    labels: list[str] = []
    for _ in range(horizon_months):
        labels.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return labels
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_charts.py -k month_labels -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/charts.py packages/web/tests/test_charts.py
git commit -m "feat(web): add month-label helper for chart x-axis"
```

---

### Task 3: Wealth-composition percentile index mapping

**Files:**
- Modify: `packages/web/web/charts.py`
- Test: `packages/web/tests/test_charts.py`

**Interfaces:**
- Consumes: `WEALTH_COMPOSITION_LOW/MID/HIGH` constants.
- Produces:
  - `wealth_percentile_index(chart_type: str, num_percentiles: int) -> int` — maps a `wealth-composition-*` chart type to a percentile row index. For `num_percentiles == 3`: low→0, mid→1, high→2. Otherwise: low→0, mid→`num_percentiles // 2`, high→`num_percentiles - 1`. Raises `ValueError` if `chart_type` is not a wealth-composition type.

- [ ] **Step 1: Write the failing tests**

```python
# add to packages/web/tests/test_charts.py
def test_wealth_index_three_percentiles_maps_low_mid_high():
    n = 3
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_LOW, n) == 0
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_MID, n) == 1
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_HIGH, n) == 2


def test_wealth_index_other_lengths_use_first_middle_last():
    n = 5
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_LOW, n) == 0
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_MID, n) == n // 2
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_HIGH, n) == n - 1


def test_wealth_index_rejects_non_wealth_chart():
    with pytest.raises(ValueError):
        charts.wealth_percentile_index(charts.PORTFOLIO, 3)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_charts.py -k wealth_index -v`
Expected: FAIL — `AttributeError` (structural). Add a `raise NotImplementedError` stub, re-run to confirm logical failure, then implement.

- [ ] **Step 3: Write the implementation**

```python
# add to packages/web/web/charts.py
_WEALTH_POSITION = {
    WEALTH_COMPOSITION_LOW: "low",
    WEALTH_COMPOSITION_MID: "mid",
    WEALTH_COMPOSITION_HIGH: "high",
}


def wealth_percentile_index(chart_type: str, num_percentiles: int) -> int:
    position = _WEALTH_POSITION.get(chart_type)
    if position is None:
        raise ValueError(f"not a wealth-composition chart: {chart_type!r}")
    if position == "low":
        return 0
    if position == "high":
        return num_percentiles - 1
    return num_percentiles // 2
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_charts.py -k wealth_index -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/charts.py packages/web/tests/test_charts.py
git commit -m "feat(web): map wealth-composition chart types to percentile rows"
```

---

### Task 4: Add Plotly dependency

**Files:**
- Modify: `packages/web/pyproject.toml`
- Modify: `uv.lock` (via `uv` only — do not hand-edit)

**Interfaces:**
- Produces: `plotly` importable inside the `web` package (`import plotly.graph_objects as go`).

- [ ] **Step 1: Add the dependency**

Run: `uv add --package life-finances-web plotly`
Expected: `uv` resolves and installs Plotly, updating `packages/web/pyproject.toml` `dependencies` and `uv.lock`.

- [ ] **Step 2: Verify import works**

Run: `uv run python -c "import plotly.graph_objects as go; print(go.Figure().to_plotly_json()['data'])"`
Expected: prints `()` or `[]` (an empty figure's data) with no `ImportError`.

- [ ] **Step 3: Commit**

```bash
git add packages/web/pyproject.toml uv.lock
git commit -m "build(web): add plotly for server-side figure JSON"
```

---

### Task 5: Band-chart figure builder (portfolio, spending-total, asset-allocation)

**Files:**
- Modify: `packages/web/web/charts.py`
- Test: `packages/web/tests/test_charts.py`

**Interfaces:**
- Consumes: `month_labels`, chart-type constants, `plotly.graph_objects`, `simulation.result.SimulationResult`.
- Produces:
  - `build_figure(result: SimulationResult, chart_type: str) -> dict` — returns a Plotly figure JSON dict (`go.Figure(...).to_plotly_json()`). This task implements the three band charts; wealth-composition is added in Task 6.
  - Band charts render **one line trace per percentile**, named `f"{p}th"` for each `p` in `result.percentiles`, in percentile order. The trace `y` values come from the matching row of the source array (`balance_start` / `withdrawals_total` / `savings_stock_allocation`). Trace `x` is `month_labels(result.start_month, result.horizon_months)`.

Note for the implementer: `SimulationResult` percentile arrays have shape `(len(percentiles), horizon_months)`; row `i` corresponds to `result.percentiles[i]` (spec §5.2 of the Phase 3d design).

- [ ] **Step 1: Write the failing tests**

```python
# add to packages/web/tests/test_charts.py
from datetime import datetime

import numpy as np

from simulation.result import SimulationResult


def _make_result(*, percentiles: list[int], horizon_months: int) -> SimulationResult:
    shape = (len(percentiles), horizon_months)
    series = np.zeros(shape, dtype=np.float64)
    months = np.zeros(horizon_months, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon_months,
        num_runs=10,
        percentiles=list(percentiles),
        start_month=(2026, 1),
        balance_start=series.copy(),
        withdrawals_essential=series.copy(),
        withdrawals_discretionary=series.copy(),
        withdrawals_general=series.copy(),
        withdrawals_total=series.copy(),
        savings_stock_allocation=series.copy(),
        wealth_job=months.copy(),
        wealth_social_security=months.copy(),
        wealth_pension=months.copy(),
        wealth_manual=months.copy(),
        num_runs_insufficient=0,
    )


def test_portfolio_has_one_trace_per_percentile_named_by_percentile():
    percentiles = [5, 50, 95]
    horizon = 4
    result = _make_result(percentiles=percentiles, horizon_months=horizon)

    figure = charts.build_figure(result, charts.PORTFOLIO)

    traces = figure["data"]
    assert len(traces) == len(percentiles)
    assert [trace["name"] for trace in traces] == [f"{p}th" for p in percentiles]


def test_band_chart_x_axis_uses_start_month_labels():
    percentiles = [50]
    horizon = 3
    result = _make_result(percentiles=percentiles, horizon_months=horizon)

    figure = charts.build_figure(result, charts.SPENDING_TOTAL)

    expected_x = charts.month_labels(result.start_month, horizon)
    assert list(figure["data"][0]["x"]) == expected_x


def test_band_chart_y_comes_from_matching_source_row():
    percentiles = [5, 95]
    horizon = 2
    result = _make_result(percentiles=percentiles, horizon_months=horizon)
    result.withdrawals_total[1, :] = np.array([111.0, 222.0])

    figure = charts.build_figure(result, charts.SPENDING_TOTAL)

    assert list(figure["data"][1]["y"]) == [111.0, 222.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_charts.py -k "portfolio or band_chart" -v`
Expected: FAIL — `AttributeError: module 'web.charts' has no attribute 'build_figure'` (structural). Add a stub `def build_figure(result, chart_type): raise NotImplementedError`, re-run to confirm a logical failure, then implement.

- [ ] **Step 3: Write the implementation**

```python
# add to packages/web/web/charts.py
import plotly.graph_objects as go

from simulation.result import SimulationResult

_BAND_SOURCE = {
    PORTFOLIO: "balance_start",
    SPENDING_TOTAL: "withdrawals_total",
    ASSET_ALLOCATION_SAVINGS: "savings_stock_allocation",
}


def _band_figure(result: SimulationResult, source_field: str) -> go.Figure:
    x = month_labels(result.start_month, result.horizon_months)
    series = getattr(result, source_field)
    figure = go.Figure()
    for row, percentile in enumerate(result.percentiles):
        figure.add_trace(
            go.Scatter(
                x=x,
                y=series[row, :].tolist(),
                mode="lines",
                name=f"{percentile}th",
            )
        )
    return figure


def build_figure(result: SimulationResult, chart_type: str) -> dict:
    source_field = _BAND_SOURCE.get(chart_type)
    if source_field is not None:
        return _band_figure(result, source_field).to_plotly_json()
    raise ValueError(f"unsupported chart type: {chart_type!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_charts.py -k "portfolio or band_chart" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/charts.py packages/web/tests/test_charts.py
git commit -m "feat(web): build band figures for portfolio/spending/allocation"
```

---

### Task 6: Wealth-composition stacked figure builder

**Files:**
- Modify: `packages/web/web/charts.py`
- Test: `packages/web/tests/test_charts.py`

**Interfaces:**
- Consumes: `wealth_percentile_index`, `month_labels`, wealth-composition constants, `build_figure` dispatcher from Task 5.
- Produces: extends `build_figure` so wealth-composition chart types return a **stacked area** figure with exactly **five** traces in this order and with these names: `"Savings"`, `"Job"`, `"Social Security"`, `"Pension"`, `"Manual"`. The `"Savings"` trace uses `result.balance_start[wealth_percentile_index(chart_type, len(result.percentiles)), :]`; the four income traces use the deterministic `wealth_job` / `wealth_social_security` / `wealth_pension` / `wealth_manual` arrays (shape `(horizon_months,)`). All five use `stackgroup="wealth"` so Plotly stacks them.

- [ ] **Step 1: Write the failing tests**

```python
# add to packages/web/tests/test_charts.py
def test_wealth_composition_has_savings_plus_four_income_layers():
    percentiles = [5, 50, 95]
    result = _make_result(percentiles=percentiles, horizon_months=3)

    figure = charts.build_figure(result, charts.WEALTH_COMPOSITION_MID)

    expected_names = ["Savings", "Job", "Social Security", "Pension", "Manual"]
    assert [trace["name"] for trace in figure["data"]] == expected_names


def test_wealth_composition_savings_trace_uses_selected_percentile_row():
    percentiles = [5, 50, 95]
    horizon = 2
    result = _make_result(percentiles=percentiles, horizon_months=horizon)
    high_index = charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_HIGH, len(percentiles))
    result.balance_start[high_index, :] = np.array([10.0, 20.0])

    figure = charts.build_figure(result, charts.WEALTH_COMPOSITION_HIGH)

    savings_trace = figure["data"][0]
    assert savings_trace["name"] == "Savings"
    assert list(savings_trace["y"]) == [10.0, 20.0]


def test_wealth_composition_traces_share_one_stackgroup():
    result = _make_result(percentiles=[5, 50, 95], horizon_months=3)

    figure = charts.build_figure(result, charts.WEALTH_COMPOSITION_LOW)

    stackgroups = {trace["stackgroup"] for trace in figure["data"]}
    assert len(stackgroups) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_charts.py -k wealth_composition -v`
Expected: FAIL — logical failure (`ValueError: unsupported chart type` raised by the Task 5 dispatcher, surfaced as a test error). This is logical, not structural (the symbol exists). Proceed to implement.

- [ ] **Step 3: Write the implementation**

```python
# add to packages/web/web/charts.py
_WEALTH_INCOME_LAYERS = (
    ("Job", "wealth_job"),
    ("Social Security", "wealth_social_security"),
    ("Pension", "wealth_pension"),
    ("Manual", "wealth_manual"),
)

_WEALTH_STACKGROUP = "wealth"


def _wealth_composition_figure(result: SimulationResult, chart_type: str) -> go.Figure:
    x = month_labels(result.start_month, result.horizon_months)
    row = wealth_percentile_index(chart_type, len(result.percentiles))
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=x,
            y=result.balance_start[row, :].tolist(),
            mode="lines",
            name="Savings",
            stackgroup=_WEALTH_STACKGROUP,
        )
    )
    for label, field in _WEALTH_INCOME_LAYERS:
        figure.add_trace(
            go.Scatter(
                x=x,
                y=getattr(result, field).tolist(),
                mode="lines",
                name=label,
                stackgroup=_WEALTH_STACKGROUP,
            )
        )
    return figure
```

Then update `build_figure` to dispatch wealth-composition types (replace the trailing `raise`):

```python
def build_figure(result: SimulationResult, chart_type: str) -> dict:
    source_field = _BAND_SOURCE.get(chart_type)
    if source_field is not None:
        return _band_figure(result, source_field).to_plotly_json()
    if chart_type in _WEALTH_POSITION:
        return _wealth_composition_figure(result, chart_type).to_plotly_json()
    raise ValueError(f"unsupported chart type: {chart_type!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_charts.py -v`
Expected: PASS (all chart tests, including Task 5).

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/charts.py packages/web/tests/test_charts.py
git commit -m "feat(web): build stacked wealth-composition figure"
```

---

### Task 7: Chart labels for the selector

**Files:**
- Modify: `packages/web/web/charts.py`
- Test: `packages/web/tests/test_charts.py`

**Interfaces:**
- Consumes: chart-type constants, `wealth_percentile_index`.
- Produces:
  - `chart_options(result: SimulationResult) -> list[tuple[str, str]]` — returns `(value, label)` pairs for every entry in `CHART_TYPES`, in order, for rendering the selector `<option>`s. Static labels: `portfolio`→`"Portfolio balance"`, `spending-total`→`"Total spending"`, `asset-allocation-savings-portfolio`→`"Savings allocation"`. Wealth-composition labels embed the actual percentile: `f"Wealth · {result.percentiles[idx]}th"` where `idx = wealth_percentile_index(value, len(result.percentiles))`.

- [ ] **Step 1: Write the failing tests**

```python
# add to packages/web/tests/test_charts.py
def test_chart_options_cover_all_chart_types_in_order():
    result = _make_result(percentiles=[5, 50, 95], horizon_months=2)

    values = [value for value, _label in charts.chart_options(result)]

    assert values == list(charts.CHART_TYPES)


def test_chart_options_wealth_labels_use_actual_percentiles():
    percentiles = [5, 50, 95]
    result = _make_result(percentiles=percentiles, horizon_months=2)

    options = dict(charts.chart_options(result))

    low_idx = charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_LOW, len(percentiles))
    assert options[charts.WEALTH_COMPOSITION_LOW] == f"Wealth · {percentiles[low_idx]}th"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_charts.py -k chart_options -v`
Expected: FAIL — `AttributeError` (structural). Add a `raise NotImplementedError` stub, re-run to confirm logical failure, then implement.

- [ ] **Step 3: Write the implementation**

```python
# add to packages/web/web/charts.py
_STATIC_LABELS = {
    PORTFOLIO: "Portfolio balance",
    SPENDING_TOTAL: "Total spending",
    ASSET_ALLOCATION_SAVINGS: "Savings allocation",
}


def chart_options(result: SimulationResult) -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    for value in CHART_TYPES:
        static = _STATIC_LABELS.get(value)
        if static is not None:
            options.append((value, static))
            continue
        idx = wealth_percentile_index(value, len(result.percentiles))
        options.append((value, f"Wealth · {result.percentiles[idx]}th"))
    return options
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_charts.py -k chart_options -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/charts.py packages/web/tests/test_charts.py
git commit -m "feat(web): provide selector options with percentile-aware labels"
```

---

### Task 8: `results.html` template + `/results` route wiring

**Files:**
- Create: `packages/web/web/templates/results.html`
- Delete: `packages/web/web/templates/results_stub.html`
- Modify: `packages/web/web/app.py` (imports; `results` route ~L327-346; `home` route TemplateResponse context ~L142-154)
- Modify: `packages/web/web/templates/index.html:16-23` (initial include + panel default chart)
- Test: `packages/web/tests/test_app.py`

**Interfaces:**
- Consumes: `web.charts.build_figure`, `web.charts.chart_options`, `web.charts.resolve_chart_type`, `web.charts.DEFAULT_CHART`.
- Produces:
  - `GET /results?plan={id}&chart={type}` returns `results.html` with context keys: `plan_id`, `result`, `chart_type` (resolved), `chart_options`, `chart_figure_json` (a JSON string of the figure dict).
  - `results.html` renders: a `<select name="chart">` whose `<option>`s come from `chart_options` with the resolved `chart_type` marked `selected`; a `<div id="results-chart">`; a `<script type="application/json" id="chart-config">{{ chart_figure_json | safe }}</script>`; a `<div id="results-meta" data-chart="{{ chart_type }}" hidden></div>`; and the retained summary line(s) (`ran_at`, `num_runs_insufficient` of `num_runs`).

Implementation notes for the route (mirror the existing pattern at `packages/web/web/app.py` L327-346):

```python
# in the imports block of packages/web/web/app.py
import json

from web import charts
```

```python
# replace _register_results_route body
def _register_results_route(web_app: FastAPI) -> None:
    @web_app.get(RESULTS, response_class=HTMLResponse)
    def results(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        chart: Annotated[str | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        settings = get_settings_repo(request).get()
        result = run_simulation(
            plan_model,
            allow_refresh=True,
            fred_api_key=settings.fred_api_key,
            eod_api_key=settings.eod_api_key,
        )
        chart_type = charts.resolve_chart_type(chart)
        figure = charts.build_figure(result, chart_type)
        return templates.TemplateResponse(
            request,
            "results.html",
            {
                "plan_id": plan_id,
                "result": result,
                "chart_type": chart_type,
                "chart_options": charts.chart_options(result),
                "chart_figure_json": json.dumps(figure),
            },
        )
```

The `home` route must render the same partial for the initial paint. Update its `index.html` context (Task 9 wires the template include). Add these keys to the `home` TemplateResponse context dict (`packages/web/web/app.py` ~L145-153), reusing its already-computed `result`:

```python
                "chart_type": charts.DEFAULT_CHART,
                "chart_options": charts.chart_options(result),
                "chart_figure_json": json.dumps(
                    charts.build_figure(result, charts.DEFAULT_CHART)
                ),
```

- [ ] **Step 1: Write the failing tests**

```python
# add to packages/web/tests/test_app.py
from web import charts as web_charts
from web.routes import RESULTS


def test_results_renders_default_chart_selected(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert 'id="results-chart"' in response.text
    assert f'data-chart="{web_charts.DEFAULT_CHART}"' in response.text


def test_results_invalid_chart_falls_back_to_default(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{RESULTS}?plan={plan_id}&chart=bogus")

    assert response.status_code == 200
    assert f'data-chart="{web_charts.DEFAULT_CHART}"' in response.text


def test_results_honors_valid_chart(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)
    chosen = web_charts.PORTFOLIO

    response = client.get(f"{RESULTS}?plan={plan_id}&chart={chosen}")

    assert response.status_code == 200
    assert f'data-chart="{chosen}"' in response.text
```

Also update `test_results_echoes_updated_balance` (`packages/web/tests/test_app.py:370-384`): the stub's `"Starting balance: ..."` text is gone. Replace its assertion body with a check that the results partial returns 200 and embeds a chart config for the plan:

```python
def test_results_returns_chart_after_balance_update(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_balance = Decimal("750000")
    patch_response: httpx.Response = client.patch(
        f"{PLAN_PORTFOLIO}?plan={plan_id}",
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )
    assert patch_response.status_code == 200

    response: httpx.Response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert 'id="chart-config"' in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_app.py -k "results" -v`
Expected: FAIL — new assertions fail against the current stub route/template (logical: 200 body lacks `id="results-chart"` / `data-chart`). If a `TemplateNotFound: results.html` error appears first, that is structural — create the template file (Step 3) and re-run to reach the logical assertions.

- [ ] **Step 3: Write the implementation**

Create `packages/web/web/templates/results.html`:

```html
<div class="results">
  <form class="chart-selector">
    <label for="chart-select">Chart</label>
    <select
      id="chart-select"
      name="chart"
      hx-get="{{ routes.RESULTS }}?plan={{ plan_id }}"
      hx-target="#results-panel"
      hx-swap="innerHTML"
      hx-trigger="change"
    >
      {% for value, label in chart_options %}
      <option value="{{ value }}" {% if value == chart_type %}selected{% endif %}>
        {{ label }}
      </option>
      {% endfor %}
    </select>
  </form>

  <div id="results-chart"></div>
  <script type="application/json" id="chart-config">{{ chart_figure_json | safe }}</script>
  <div id="results-meta" data-chart="{{ chart_type }}" hidden></div>

  <p class="results-summary">
    {{ result.num_runs_insufficient }} of {{ result.num_runs }} runs ran out of money
    · updated {{ result.ran_at.strftime("%Y-%m-%d %H:%M:%S") }}
  </p>
</div>
```

Apply the `app.py` route + home-context changes shown in the Interfaces block above. Delete `packages/web/web/templates/results_stub.html`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_app.py -k "results" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/app.py packages/web/web/templates/results.html packages/web/tests/test_app.py
git rm packages/web/web/templates/results_stub.html
git commit -m "feat(web): render results chart partial with selector and fallback"
```

---

### Task 9: Shell wiring — Plotly CDN, initial include, and re-init on swap

**Files:**
- Modify: `packages/web/web/templates/base.html:8` (add plotly.js CDN)
- Modify: `packages/web/web/templates/index.html:16-23` (include `results.html`; keep panel `hx-get` on default chart) and its `<script>` block (L26-58)
- Test: `packages/web/tests/test_app.py`

**Interfaces:**
- Consumes: `results.html`, `#results-meta[data-chart]`, `#chart-config` from Task 8.
- Produces:
  - `base.html` loads plotly.js once from CDN.
  - `index.html` initial results include renders `results.html` (not the deleted stub).
  - Shell JS: a `renderResultsChart()` function reads the JSON from `#chart-config`, calls `Plotly.react("results-chart", figure.data, figure.layout, {responsive: true})`, then syncs `#results-panel`'s `hx-get` to `{{ routes.RESULTS }}?plan={plan}&chart={dataChart}` and calls `htmx.process` on the panel. It runs once on `DOMContentLoaded` and on every `htmx:afterSwap` whose target is `#results-panel`.

- [ ] **Step 1: Write the failing test**

```python
# add to packages/web/tests/test_app.py
def test_home_loads_plotly_and_results_partial(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert "plotly" in response.text.lower()
    assert 'id="results-chart"' in response.text
    assert "results-stub" not in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/web/tests/test_app.py -k plotly_and_results_partial -v`
Expected: FAIL — logical: home still includes the stub / lacks the plotly script and `#results-chart`.

- [ ] **Step 3: Write the implementation**

In `packages/web/web/templates/base.html`, add after the htmx script (L8):

```html
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
```

In `packages/web/web/templates/index.html`, replace the results-panel include (L16-23) so it renders the real partial and defaults the chart param:

```html
  <div
    id="results-panel"
    hx-get="{{ routes.RESULTS }}?plan={{ plan_id }}&chart={{ chart_type }}"
    hx-trigger="planUpdated from:body"
    hx-swap="innerHTML"
  >
    {% include "results.html" %}
  </div>
```

Add to the `index.html` `<script>` block (after the existing handlers, before `{% endblock %}`):

```html
  const resultsPanel = document.getElementById("results-panel");

  function renderResultsChart() {
    const config = document.getElementById("chart-config");
    const meta = document.getElementById("results-meta");
    if (!config || !meta || typeof Plotly === "undefined") return;
    const figure = JSON.parse(config.textContent);
    Plotly.react("results-chart", figure.data, figure.layout, { responsive: true });
    const chart = meta.getAttribute("data-chart");
    resultsPanel.setAttribute(
      "hx-get",
      "{{ routes.RESULTS }}?plan={{ plan_id }}&chart=" + encodeURIComponent(chart)
    );
    htmx.process(resultsPanel);
  }

  document.addEventListener("DOMContentLoaded", renderResultsChart);

  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "results-panel") {
      renderResultsChart();
    }
  });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/web/tests/test_app.py -k plotly_and_results_partial -v`
Expected: PASS

- [ ] **Step 5: Run the full web suite**

Run: `uv run pytest packages/web -v`
Expected: PASS (no lingering `results_stub` references).

- [ ] **Step 6: Commit**

```bash
git add packages/web/web/templates/base.html packages/web/web/templates/index.html packages/web/tests/test_app.py
git commit -m "feat(web): load plotly and re-render results chart on htmx swap"
```

---

### Task 10: Documentation & index corrections

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` (Phase 4b deliverable ~L405; exit criteria ~L411-418; umbrella exit item ~L368; Active phase / completed table)
- Modify: `packages/web/AGENTS.md` (add results `?chart=` + Plotly note)
- Modify: `docs/superpowers/specs/2026-07-15-phase-4b-core-charts-design.md` (set `Status: Approved`)

**Interfaces:** documentation only; no code.

- [ ] **Step 1: Correct the rebuild index Phase 4b section**

Replace the Phase 4b **Delivers** line (`docs/superpowers/plans/2026-06-12-rebuild-index.md:405`) so it drops `withdrawal` and the false funding-sources equivalence, and lists the shipped charts:

```markdown
**Delivers:** Replace `results_stub.html` with server-rendered Plotly charts (CDN plotly.js + `Plotly.react` after HTMX swaps); chart-type selector via `?chart=`; core chart types backed by `SimulationResult`: `portfolio`, `spending-total`, `asset-allocation-savings-portfolio`, and `wealth-composition-{low,mid,high}` (savings percentile band + deterministic tax-prorated income-source NPV layers). tpaw-style spending funding-sources / per-stream charts remain deferred to 4e.
```

Update the Phase 4b **Exit criteria** (`:411-418`) to:

```markdown
- [ ] Results partial renders portfolio, spending-total, savings-allocation, and wealth-composition charts
- [ ] Chart type selector switches among shipped core types via `?chart=`; selection survives `planUpdated` refresh
- [ ] X-axis uses `SimulationResult.start_month` + horizon months
- [ ] Percentile bands use `result.percentiles` (default `[5, 50, 95]`)
- [ ] `make` passes; debounced results refresh still works
```

Update the umbrella exit item (`:368`) `- [ ] Core tpaw charts in results panel (4b)` → `- [x] Core charts in results panel (4b)`.

- [ ] **Step 2: Update the Active phase / completed table**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, set the Active phase table (L37-40) to Phase 4c, and add a Phase 4b row to the Completed plans table (L562+):

```markdown
| Phase 4b | `2026-06-12-phase-4b-core-charts.md` | complete |
```

Set the "Next step" section (L578-580) to point at Phase 4c.

- [ ] **Step 3: Add a `web/AGENTS.md` note**

Under the Settings / template conventions area of `packages/web/AGENTS.md`, add:

```markdown
### Results charts

`GET /results?plan={id}&chart={type}` renders `results.html`. Valid `chart` values are the constants in `web/charts.py` (`CHART_TYPES`); unknown values fall back to `DEFAULT_CHART` (`spending-total`). Figures are built server-side as Plotly JSON (`web.charts.build_figure`); plotly.js loads once from CDN in `base.html`. The shell calls `Plotly.react` on load and on every `htmx:afterSwap` targeting `#results-panel`, and mirrors the selected chart onto the panel's `hx-get` so `planUpdated` refreshes keep the selection.
```

- [ ] **Step 4: Mark the spec approved**

In `docs/superpowers/specs/2026-07-15-phase-4b-core-charts-design.md`, change the status line to `**Status:** Approved`.

- [ ] **Step 5: Verify the whole suite and lint**

Run: `make`
Expected: PASS (ruff + pyright + pytest across packages).

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/plans/2026-06-12-rebuild-index.md packages/web/AGENTS.md docs/superpowers/specs/2026-07-15-phase-4b-core-charts-design.md
git commit -m "docs: record phase 4b charts, correct chart naming, mark 4b complete"
```

---

## Self-Review

**Spec coverage:**
- Plotly embed, CDN once, `Plotly.react` after swap → Tasks 4, 8, 9.
- Web-owned figure builders → Tasks 5–7.
- `?chart=` routing + fallback → Tasks 1, 8.
- Chart types portfolio / spending-total / savings-allocation / wealth-composition-{low,mid,high} → Tasks 5, 6.
- Omit `withdrawal`; defer tpaw funding-sources → not implemented (correctly absent); documented in Task 10.
- X-axis from `start_month` + horizon → Task 2, exercised in Task 5.
- Percentile bands from `result.percentiles` → Tasks 5, 7.
- Selection survives `planUpdated` → Task 9 (panel `hx-get` sync).
- Error handling (invalid chart fallback, summary retained) → Tasks 1, 8.
- Tests without browser/network → all tasks (TestClient + pure builders).
- Docs / index / AGENTS corrections → Task 10.

**Placeholder scan:** No TBD/TODO; every code step shows complete code; commands include expected output.

**Type consistency:** `build_figure(result, chart_type) -> dict`, `resolve_chart_type`, `month_labels`, `wealth_percentile_index`, `chart_options`, and the `results.html` context keys (`plan_id`, `result`, `chart_type`, `chart_options`, `chart_figure_json`) are used consistently across Tasks 1–9.

**Testing policy check:** Tests import chart constants/defaults from `web.charts` (no copied literals); shared values (`percentiles`, `horizon`, `expected_balance`, `chosen`) are bound once and referenced in both arrange and assert; each test targets one behavior; red-green steps call out structural-vs-logical failure explicitly.
