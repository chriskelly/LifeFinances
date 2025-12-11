# Tasks: Disability Insurance Calculator Script

**Input**: Design documents from `/specs/001-disability-insurance-calculator/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Tests are OPTIONAL per constitution - this is a standalone notebook exempted from testing requirements.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Standalone notebook**: `standalone_tools/` at repository root
- Notebook cells organized by functionality within single notebook file

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create `/workspace/standalone_tools` directory
- [X] T002 Create Jupyter notebook file `/workspace/standalone_tools/disability_insurance_calculator.ipynb`
- [X] T003 Add notebook header cell with title, description, and imports in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (CRITICAL: must include workspace root path handling - determine workspace root, add to sys.path, os.chdir to workspace root - and Flask initialization skipping - set SKIP_FLASK_INIT=1 environment variable - all BEFORE any app module imports)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement config loading function in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (load user config from YAML file, extract user_disability_coverage and partner_disability_coverage fields: percentage and duration_years)
- [X] T005 Implement config validation function in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (check for income profiles, handle edge cases: no profiles, already retired)
- [X] T006 Implement Benefit cutoff age configuration in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (configurable in script, default value is 65, but user must be able to set a different Benefit cutoff age)
- [X] T007 Implement helper function `set_fixed_inflation()` in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (following tpaw_planner.ipynb pattern: takes SimulationEngine and inflation_rate, sets deterministic cumulative inflation path using interval_yield, overrides engine._economic_sim_data.inflation for all trials)
- [X] T008 Implement helper function to modify engine._user_config.income_profiles to zero out job income in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (following tpaw_planner.ipynb pattern of modifying engine data directly)
- [X] T009 Implement helper function to extract current annual income (first profile with income > $0) in `/workspace/standalone_tools/disability_insurance_calculator.ipynb`
- [X] T010 Implement helper function to calculate years until Benefit cutoff age in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (use configurable Benefit cutoff age, default 65)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Calculate Disability Insurance Needs for User (Priority: P1) 🎯 MVP

**Goal**: Calculate total income replacement needed, existing coverage replacement (after taxes), and remaining coverage gap for user disability scenario

**Independent Test**: Can be fully tested by providing user income profile and existing coverage, then verifying the script calculates total replacement needs, existing coverage replacement (after taxes), and remaining gap. Delivers value by helping users understand their coverage adequacy.

### Implementation for User Story 1

- [X] T011 [US1] Implement baseline scenario execution in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (create SimulationEngine with config_path, call set_fixed_inflation() to set deterministic inflation rate, run gen_all_trials(), extract results DataFrame)
- [X] T012 [US1] Add sanity check output for baseline scenario in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (display baseline income totals: job, SS, pension)
- [X] T013 [US1] Implement disability scenario execution in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (modify engine._user_config.income_profiles directly to zero user job income, clear results with engine.results = Results(), run gen_all_trials() again - fixed inflation already set from baseline, extract results DataFrame)
- [X] T014 [US1] Add sanity check output for disability scenario in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (display disability income totals: job=0, reduced SS, reduced pension)
- [X] T015 [US1] Implement income comparison calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (calculate lost job income until Benefit cutoff age, reduced SS lifetime including post-Benefit cutoff age, reduced pension lifetime including post-Benefit cutoff age. **Note**: Sum quarterly values directly - do NOT annualize by multiplying by INTERVALS_PER_YEAR, as each interval already represents quarterly income)
- [X] T015a [US1] Verify Social Security and pension calculation integration in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (verify that baseline and disability scenarios properly reflect Social Security and pension benefit differences when job income is zeroed out, per FR-011 and FR-012)
- [X] T016 [US1] Add sanity check output for income comparison in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (display income differences: lost job, reduced SS, reduced pension)
- [X] T017 [US1] Implement total replacement needs calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (calculate post-tax income for baseline and disability scenarios: (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes), then total replacement needs = baseline post-tax income - disability post-tax income, includes post-Benefit cutoff age reductions, per FR-005 and FR-008. **Note**: Sum quarterly values directly - do NOT annualize, as each interval already represents quarterly income)
- [X] T018 [US1] Implement existing coverage replacement calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (extract job income from baseline, apply coverage percentage capped at 100%, calculate taxes on benefits using average tax rate from baseline scenario: (total income taxes + total Medicare taxes) / total income for coverage period, sum net after-tax benefits over coverage duration, per FR-007. **Note**: Sum quarterly values directly - do NOT annualize, as each interval already represents quarterly income)
- [X] T019 [US1] Add sanity check output for coverage replacement calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (display coverage breakdown: gross benefits, taxes, net benefits)
- [X] T020 [US1] Implement coverage gap calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (total needs - existing coverage, ensure gap >= 0)
- [X] T021 [US1] Implement benefit percentage calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (formula per FR-008: (Coverage gap / Years until Benefit cutoff age) / Current annual income, where coverage gap = total replacement needs - existing coverage replacement)
- [X] T022 [US1] Implement structured output formatting for user scenario in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (display: total replacement needed, existing coverage replacement, remaining gap, recommended coverage percentage and duration)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. User can calculate their own disability insurance needs.

---

## Phase 4: User Story 3 - Calculate Disability Insurance Needs for Partner (Priority: P2)

**Goal**: Calculate disability insurance needs for partner, accounting for how partner's disability would affect household income and future benefits

**Independent Test**: Can be fully tested by providing partner income profile and existing coverage, then verifying the script calculates partner's total replacement needs, existing coverage replacement, and remaining gap. Delivers value by enabling comprehensive household financial protection planning.

### Implementation for User Story 3

- [X] T023 [US3] Implement partner baseline scenario execution in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (create new SimulationEngine with config_path to restore original config, call set_fixed_inflation() to set deterministic inflation rate, run gen_all_trials() for partner baseline - reuse baseline results from user scenario)
- [X] T024 [US3] Implement partner disability scenario execution in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (modify engine._user_config.partner.income_profiles directly to zero partner job income, clear results, run gen_all_trials() again - fixed inflation already set from baseline, extract results DataFrame)
- [X] T025 [US3] Implement partner income comparison calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (calculate lost partner job income, reduced partner SS including post-Benefit cutoff age, reduced partner pension including post-Benefit cutoff age. **Note**: Sum quarterly values directly - do NOT annualize by multiplying by INTERVALS_PER_YEAR, as each interval already represents quarterly income)
- [X] T025a [US3] Verify partner Social Security and pension calculation integration in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (verify that partner baseline and disability scenarios properly reflect Social Security and pension benefit differences when partner job income is zeroed out, per FR-011 and FR-012)
- [X] T026 [US3] Implement partner total replacement needs calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (calculate post-tax income for baseline and partner disability scenarios: (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes), then partner total replacement needs = baseline post-tax income - partner disability post-tax income, per FR-006 and FR-008. **Note**: Sum quarterly values directly - do NOT annualize, as each interval already represents quarterly income)
- [X] T027 [US3] Implement partner existing coverage replacement calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (apply partner coverage percentage capped at 100%, calculate taxes using average tax rate from baseline scenario: (total income taxes + total Medicare taxes) / total income for coverage period, sum net benefits, per FR-007. **Note**: Sum quarterly values directly - do NOT annualize, as each interval already represents quarterly income)
- [X] T028 [US3] Implement partner coverage gap calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (partner total needs - partner existing coverage)
- [X] T029 [US3] Implement partner benefit percentage calculation in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (formula per FR-008: (Partner coverage gap / Years until Benefit cutoff age) / Partner current annual income, where partner coverage gap = partner total replacement needs - partner existing coverage replacement)
- [X] T030 [US3] Implement structured output formatting for partner scenario in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (display partner results separately from user results)

**Checkpoint**: At this point, User Stories 1 AND 3 should both work independently. User can calculate needs for both themselves and their partner.

---

## Phase 5: Edge Cases & Error Handling

**Purpose**: Handle edge cases gracefully with clear error messages

- [X] T031 Implement edge case handling for no user income profiles in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (focus only on partner if partner has income profiles)
- [X] T032 Implement edge case handling for neither user nor partner having income profiles in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (exit with clear message: "No disability insurance needed - no future income to protect")
- [X] T033 Implement edge case handling for already retired in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (check if all income profiles have zero income, exit with message: "No disability insurance needed - already retired")
- [X] T034 Implement edge case handling for coverage percentage > 100% in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (cap at 100% for gap calculation but display actual percentage in output)
- [X] T035 Implement edge case handling for coverage duration beyond Benefit cutoff age in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (apply coverage until Benefit cutoff age, handle gracefully)
- [X] T036 Implement edge case handling for user on sabbatical (current income = $0) in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (use first future income profile with income > $0 for benefit percentage calculation)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T037 [P] Add comprehensive docstrings and comments throughout `/workspace/standalone_tools/disability_insurance_calculator.ipynb` explaining calculation logic
- [X] T038 [P] Verify notebook follows `tpaw_planner.ipynb` pattern and style in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (including set_fixed_inflation usage)
- [X] T039 [P] Add markdown cells explaining each major section in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (config loading, baseline scenario, disability scenario, calculations, output)
- [X] T040 [P] Verify all sanity check outputs are clear and informative in `/workspace/standalone_tools/disability_insurance_calculator.ipynb`
- [X] T041 [P] Ensure structured output matches spec requirements (total needs, existing coverage, gap, benefit percentage) in `/workspace/standalone_tools/disability_insurance_calculator.ipynb`
- [X] T042 [P] Verify calculations complete in under 2 minutes per user (performance requirement)
- [X] T043 [P] Add error handling for SimulationEngine failures in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (clear error messages)
- [X] T044 [P] Verify notebook can handle missing disability coverage config gracefully in `/workspace/standalone_tools/disability_insurance_calculator.ipynb` (default to 0% coverage)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 (Phase 3) can start after Foundational
  - User Story 3 (Phase 4) can start after Foundational (independent of US1)
  - Edge Cases (Phase 5) depends on US1 and US3 completion
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories. Includes secondary effects (US2) and tax handling (US4) integrated.
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independent of US1, can be implemented in parallel. Includes secondary effects and tax handling integrated.

**Note**: User Story 2 (Secondary Effects) and User Story 4 (Tax Implications) are integrated into US1 and US3, not separate phases.

### Within Each User Story

- Config loading before scenario execution
- Baseline scenario before disability scenario (modify engine data, clear results, run again)
- Income comparison before gap calculation
- Coverage replacement calculation before gap calculation
- Calculations before output formatting

### Parallel Opportunities

- All Setup tasks can run sequentially (notebook creation)
- All Foundational helper functions marked [P] can be implemented in parallel cells
- User Story 1 and User Story 3 can be implemented in parallel (different scenarios)
- Polish tasks marked [P] can run in parallel

---

## Parallel Example: Foundational Phase

```python
# These helper functions can be implemented in parallel cells:
# Cell 1: Config loading function
# Cell 2: Config validation function
# Cell 3: Benefit cutoff age configuration (configurable, default 65)
# Cell 4: set_fixed_inflation helper function (set deterministic inflation rate)
# Cell 5: Engine data modification function (zero out income profiles)
# Cell 6: Current annual income extraction function
# Cell 7: Years until Benefit cutoff age calculation function
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (create notebook)
2. Complete Phase 2: Foundational (config loading, validation, helpers)
3. Complete Phase 3: User Story 1 (user disability scenario calculation)
4. **STOP and VALIDATE**: Test User Story 1 independently with sample config
5. Verify output matches spec requirements

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Verify output (MVP!)
3. Add User Story 3 → Test independently → Verify partner scenario works
4. Add Edge Cases → Test edge cases → Verify graceful handling
5. Add Polish → Finalize documentation and formatting

### Single Developer Strategy

Since this is a single notebook:

1. Complete Setup + Foundational sequentially
2. Implement User Story 1 completely (all cells):
   - Create engine with config_path, call set_fixed_inflation() to set deterministic inflation, run baseline
   - Modify engine._user_config.income_profiles directly, clear results, run disability (fixed inflation already set)
3. Test User Story 1 with sample config
4. Implement User Story 3 (create new engine to restore config, call set_fixed_inflation(), modify partner income, run scenarios)
5. Add edge case handling
6. Polish and document

---

## Notes

- [P] tasks = can be implemented in parallel notebook cells (no dependencies)
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Notebook cells should have clear markdown headers explaining each section
- Add sanity check outputs throughout for verification
- Commit after each major phase completion
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, unclear cell organization, missing sanity checks
