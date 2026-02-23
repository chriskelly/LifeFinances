# Research: Spending Controller

**Feature**: 001-spending-controller  
**Date**: 2026-01-01  
**Purpose**: Research technical decisions and patterns for implementing the spending controller

## Research Questions

### Q1: Controller Pattern Implementation

**Question**: What is the established controller pattern used in the allocation controller, and how should we adapt it for spending?

**Findings**:

The allocation controller (`app/models/controllers/allocation.py`) follows this pattern:

1. **Abstract Strategy Base Class** (`_Strategy`):
   - ABC with abstract method `gen_allocation(state, controllers=None)`
   - Returns calculation result (for allocation: np.ndarray)
   - Accepts optional Controllers parameter for cross-controller dependencies

2. **Concrete Strategy Classes** (e.g., `_FlatAllocationStrategy`, `_NetWorthPivotStrategy`):
   - Dataclasses decorated with `@dataclass`
   - Store configuration and pre-computed values
   - Implement the abstract method from base class
   - Use `__post_init__` for initialization logic (e.g., converting config to arrays)

3. **Controller Class** (`Controller`):
   - Public interface for the subsystem
   - `__init__` takes User and any context needed (e.g., asset_lookup for allocation)
   - Selects and instantiates the appropriate strategy based on config
   - Uses match/case statement to handle strategy selection
   - Delegates calculation to the selected strategy via public method

4. **Integration**:
   - Controller added to `Controllers` dataclass in `app/models/controllers/__init__.py`
   - Used by other components (e.g., `StateChangeComponents`) by accessing `controllers.allocation`

**Decision**: Follow the exact same pattern for spending controller.

**Rationale**: Proven architecture with clear separation of concerns. Strategy pattern allows future extension (e.g., guardrails, percentage-based spending). Match/case provides type-safe strategy selection.

**Alternatives Considered**:
- Simple function approach: Rejected because it doesn't provide extensibility for future strategies
- Strategy registration pattern: Rejected as unnecessary complexity for the current use case

---

### Q2: Spending Calculation Interface

**Question**: What should the spending controller's public API look like, and what does it return?

**Findings**:

Current implementation (`app/models/financial/state_change.py`, line 140-156):
```python
@staticmethod
def _calc_spending(components: StateChangeComponents) -> float:
    config = components.state.user.spending
    inflation = components.state.inflation
    
    for profile in config.profiles:
        if not profile.end_date or profile.end_date >= components.state.date:
            return -profile.yearly_amount / INTERVALS_PER_YEAR * inflation
    raise ValueError("No spending profile found for the current date")
```

Key observations:
- Returns a single float (negative value)
- Needs State object (for date, inflation, user config)
- Uses `INTERVALS_PER_YEAR` constant (value: 4 for quarterly)
- Returns negative value to represent outflow

**Decision**: Controller method signature:
```python
def calc_spending(self, state: State) -> float:
```

**Rationale**: 
- Matches the semantic meaning (calculate spending for a given state)
- Consistent with other controllers (e.g., pension, social_security use `calc_payment`)
- Simple interface - strategies don't need Controllers parameter (spending is self-contained)
- Returns float (not numpy array) since spending is a scalar value

**Alternatives Considered**:
- `gen_spending`: Rejected because "generate" implies creation, while we're calculating a value
- Taking controllers parameter: Rejected because spending calculation doesn't depend on other controllers

---

### Q3: Configuration Structure

**Question**: How should the new configuration structure work, given the requirement to move `spending_strategy` to root level?

**Findings**:

Current structure (in `app/models/config/spending.py`):
```python
class Spending(BaseModel):
    spending_strategy: SpendingOptions = Field(default_factory=...)
    profiles: list[SpendingProfile]
```

Required new structure (from spec):
```yaml
spending_strategy:
  inflation_following:
    chosen: true
    profiles:
      - yearly_amount: 60
        end_date: 2035.25
      - ...
```

Pattern from allocation (in `app/models/config/allocation.py`):
```python
class AllocationStrategy(StrategyOptions):
    flat: FlatAllocationStrategyConfig = FlatAllocationStrategyConfig()
    net_worth_pivot: NetWorthPivotStrategyConfig = NetWorthPivotStrategyConfig()
    total_portfolio: TotalPortfolioStrategyConfig = TotalPortfolioStrategyConfig()
```

Each strategy config extends `StrategyConfig`:
```python
class FlatAllocationStrategyConfig(StrategyConfig):
    allocation: dict[str, float] = Field(...)
```

**Decision**: Create new config structure:

1. **InflationFollowingConfig** (extends StrategyConfig):
   ```python
   class InflationFollowingConfig(StrategyConfig):
       profiles: list[SpendingProfile] = Field(...)
       
       @model_validator(mode="after")
       def validate_profiles(self):
           # Move validation from Spending class here
   ```

2. **SpendingStrategyOptions** (extends StrategyOptions):
   ```python
   class SpendingStrategyOptions(StrategyOptions):
       inflation_following: InflationFollowingConfig = Field(
           default_factory=lambda: InflationFollowingConfig(chosen=True)
       )
   ```

3. **User model update**:
   - Change from `spending: Spending` to `spending_strategy: SpendingStrategyOptions`
   - Remove the old `Spending` and `SpendingOptions` classes

**Rationale**:
- Follows established pattern from allocation
- StrategyConfig provides `chosen` field and `chosen_strategy` property
- Profiles belong to the strategy, not at root level
- Validation stays with the data it validates

**Alternatives Considered**:
- Keep Spending wrapper: Rejected because spec explicitly requires root-level `spending_strategy`
- Move validation to controller: Rejected because validation belongs in config layer (Pydantic models)

---

### Q4: Profile Selection Logic

**Question**: What is the correct profile selection logic given the clarification about date boundaries?

**Findings**:

From clarifications:
- Q: When simulation date equals a profile's end_date, which profile should be active?
- A: Current profile remains active (date <= end_date) - transition happens after end_date

Current logic:
```python
if not profile.end_date or profile.end_date >= components.state.date:
    return -profile.yearly_amount / INTERVALS_PER_YEAR * inflation
```

This uses `>=` which means "profile is active when end_date >= current_date", equivalent to "date <= end_date".

**Decision**: Keep the same logic in the new implementation:

```python
for profile in self.profiles:
    if profile.end_date is None or state.date <= profile.end_date:
        return -profile.yearly_amount / INTERVALS_PER_YEAR * state.inflation
```

**Rationale**:
- Matches clarification answer
- Maintains backward compatibility
- Intuitive: profile with end_date 2035.25 is active throughout the quarter ending at 2035.25

**Alternatives Considered**:
- `date < end_date` (strict less than): Rejected because it contradicts the clarification

---

### Q5: Validation Strategy

**Question**: When and how should profile validation occur?

**Findings**:

From clarifications, all validation should happen at initialization (fail-fast):
- Empty/malformed profiles → validation error at init
- Last profile with end_date → validation error at init
- Non-chronological profiles → validation error at init

Current validation in `Spending.validate_profiles()` runs during Pydantic model validation.

**Decision**: Keep validation in Pydantic model (now in `InflationFollowingConfig`):

1. Move `_spending_profiles_validation` function as-is
2. Keep `@model_validator(mode="after")` decorator
3. Validation runs when config is loaded (before controller creation)
4. Controller can assume profiles are valid

**Rationale**:
- Validation belongs in the config layer (Pydantic models)
- Fails early (during config load, before simulation starts)
- Controller doesn't need defensive checks (profiles are guaranteed valid)
- Follows existing pattern (validation in config, not controller)

**Alternatives Considered**:
- Validate in controller `__init__`: Rejected because it's too late and violates separation of concerns
- Skip validation: Rejected because clarifications explicitly require fail-fast validation

---

### Q6: Constants and Imports

**Question**: Where is `INTERVALS_PER_YEAR` defined, and what other imports are needed?

**Findings**:

From `state_change.py` imports:
```python
from app.data.constants import INTERVALS_PER_YEAR
```

From `allocation.py` imports:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast
from app.models.config import User
from app.models.financial.state import State
```

**Decision**: Spending controller imports:

```python
"""Module for spending calculation strategies

Classes:
    Controller: Manages strategy and spending calculation
        calc_spending(self, state: State) -> float:
        Returns spending amount for a given state
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.data.constants import INTERVALS_PER_YEAR
from app.models import config
from app.models.config import User
from app.models.financial.state import State

if TYPE_CHECKING:
    from app.models.controllers import Controllers
```

**Rationale**:
- Follows allocation controller import pattern exactly
- TYPE_CHECKING import prevents circular dependency
- Minimal imports (only what's needed)

**Alternatives Considered**:
- Import specific config classes: Rejected in favor of `from app.models import config` for consistency

---

## Summary of Technical Decisions

| Decision Area | Choice | Rationale |
|--------------|--------|-----------|
| **Architecture** | Controller + Strategy pattern | Follows allocation pattern; enables future strategies |
| **Method Name** | `calc_spending(state) -> float` | Semantic clarity; matches other payment controllers |
| **Config Structure** | Root-level `spending_strategy` with nested `inflation_following` | Follows allocation pattern; spec requirement |
| **Profile Selection** | `date <= end_date` | Matches clarification; intuitive boundary behavior |
| **Validation** | Pydantic model validators | Fail-fast at config load; separation of concerns |
| **Return Value** | Negative float | Maintains existing convention (outflow as negative) |
| **Dependencies** | No Controllers parameter needed | Spending is self-contained calculation |

## Open Questions

None. All technical decisions resolved through research and clarifications.

