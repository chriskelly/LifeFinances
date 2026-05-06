# Data Model: Split Configuration UI and Simulation Backend

**Date**: 2026-04-05  
**Feature**: Split Configuration UI and Simulation Backend  
**Phase**: 1 – Design

## Persistence

| Item | Description |
|------|-------------|
| **Config file** | Path `config.yml` at process working directory (see `app.data.constants.CONFIG_PATH`). If missing, `read_config_file` falls back to `tests/sample_configs/full_config.yml` when path equals default — preserve this behavior for parity unless product decides otherwise. |
| **Simulation output** | Not persisted across sessions; only latest run returned to client per FR-004a. |

---

## Resource: ConfigDocument

Represents the **active configuration** as raw text exchanged between client and API.

| Field | Type | Rules |
|-------|------|--------|
| `content` | `string` | Full YAML text; must pass existing `write_config_file` validation when saving (YAML parse + `User` Pydantic model). |

**Operations**:

- **Read**: Load from disk via `read_config_file()`.
- **Write**: Persist via `write_config_file(content=...)`.

**Validation** (server-side, unchanged from today):

- Valid YAML.
- Pydantic `User` model validation; failures → client-facing error (400).

---

## Resource: SimulationResult

Represents the **latest** simulation response for the UI (no history).

| Field | Type | Rules |
|-------|------|--------|
| `success_percentage` | `string` | Display value matching current template (`IndexPage` uses string from `calc_success_percentage()`). |
| `first_result` | `FirstResultTable` | First trial dataframe in pandas split format (`columns` + `data`). |

### Embedded type: FirstResultTable

| Field | Type | Rules |
|-------|------|--------|
| `columns` | `string[]` | Column names from `DataFrame.columns`. |
| `data` | `array[]` | Row values aligned to `columns`; serialized from `DataFrame.to_json(orient="split")` and decoded to JSON-native values (number, string, boolean, or null). |

**Source**: `gen_simulation_results()` → `as_dataframes()[0]` converted to column/row form (implementation detail: `DataFrame.to_dict(orient="split")` or explicit iteration).

**Errors**:

- Simulation failure → 500 (or 422 if classified as bad config state) with JSON `error` object; client shows message and keeps editor state.

---

## State transitions (client UX)

1. **Load** → GET config → editor shows `content`.
2. **Save** (button 1) → **PUT `/api/config`** with editor text → server validates and writes → success feedback.
3. **Save & run** (button 2) → **PUT `/api/config`** with editor text; on success → **POST `/api/simulation/run`** → show `success_percentage` and `first_result`. If **PUT** fails, **do not** call **POST**.
4. **No standalone run**: The UI MUST NOT offer an action that calls **POST `/api/simulation/run`** without having performed **PUT `/api/config`** in the same **Save & run** flow (parity with legacy; no “run without saving” from the user’s perspective).

---

## Concurrency

| Scenario | Rule |
|----------|------|
| Multiple browser tabs | **Last-write-wins** on `PUT /api/config` unless implementation adds ETags later (out of scope for MVP). Document in README/quickstart. |

---

## API-to-domain mapping

| Endpoint | Domain function |
|----------|-----------------|
| `GET /api/config` | `read_config_file()` |
| `PUT /api/config` | `write_config_file(content)` |
| `POST /api/simulation/run` | `gen_simulation_results()` after file is authoritative |

No new database entities.
