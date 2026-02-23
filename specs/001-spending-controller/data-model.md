# Data Model: Spending Controller

**Feature**: 001-spending-controller  
**Date**: 2026-01-01  
**Purpose**: Define entities, relationships, and data structures for the spending controller

## Entity Diagram

```text
┌─────────────────────────────┐
│ User                        │
│ (existing, in config/user.py)│
├─────────────────────────────┤
│ - spending_strategy         │───┐
│   : SpendingStrategyOptions │   │
└─────────────────────────────┘   │
                                  │
                                  │ 1
                                  │
                                  ▼
┌──────────────────────────────────────┐
│ SpendingStrategyOptions              │
│ (new, in config/spending.py)         │
├──────────────────────────────────────┤
│ + inflation_following                │───┐
│   : InflationFollowingConfig         │   │
│   (default chosen=True)              │   │
└──────────────────────────────────────┘   │
         ▲                                  │ 1
         │ extends                          │
         │                                  ▼
┌─────────────────┐            ┌────────────────────────────┐
│ StrategyOptions │            │ InflationFollowingConfig   │
│ (base class)    │            │ (new, config/spending.py)  │
└─────────────────┘            ├────────────────────────────┤
                               │ + chosen: bool             │
                               │ + profiles: list           │───┐
                               │   [SpendingProfile]        │   │
                               │                            │   │
                               │ @model_validator           │   │
                               │ validate_profiles()        │   │ 1..*
                               └────────────────────────────┘   │
                                        ▲                        │
                                        │ extends                │
                                        │                        ▼
                               ┌─────────────────┐   ┌──────────────────────┐
                               │ StrategyConfig  │   │ SpendingProfile      │
                               │ (base class)    │   │ (existing, reused)   │
                               ├─────────────────┤   ├──────────────────────┤
                               │ + chosen: bool  │   │ + yearly_amount: int │
                               │ + chosen_strategy│  │ + end_date: float?   │
                               └─────────────────┘   └──────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Controller Entities (runtime, not config)                   │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────┐
│ Controllers              │
│ (updated, __init__.py)   │
├──────────────────────────┤
│ + spending: Controller   │◄───────┐
│ + allocation: Controller │        │
│ + job_income: Controller │        │
│ ...                      │        │
└──────────────────────────┘        │ instantiates
                                    │
                                    │
┌───────────────────────────────────┴───┐
│ spending.Controller                   │
│ (new, controllers/spending.py)        │
├───────────────────────────────────────┤
│ - _strategy: _Strategy                │───┐
│                                       │   │
│ + __init__(user: User)                │   │
│ + calc_spending(state: State)         │   │ delegates to
│   -> float                            │   │
└───────────────────────────────────────┘   │
                                            │
                                            ▼
┌────────────────────────────────────────────────┐
│ _Strategy (ABC)                                │
│ (new, controllers/spending.py)                 │
├────────────────────────────────────────────────┤
│ + calc_spending(state: State) -> float         │
│   [abstract]                                   │
└────────────────────────────────────────────────┘
                ▲
                │ implements
                │
┌───────────────┴────────────────────────────────┐
│ _InflationFollowingStrategy                    │
│ (new, controllers/spending.py)                 │
├────────────────────────────────────────────────┤
│ - config: InflationFollowingConfig             │
│ - profiles: list[SpendingProfile]              │
│   (extracted from config for fast access)      │
│                                                │
│ + __post_init__()                              │
│ + calc_spending(state: State) -> float         │
│   - Select profile by date                     │
│   - Calculate: -yearly_amount/4 * inflation    │
└────────────────────────────────────────────────┘
```

## Entity Definitions

### Configuration Entities

#### SpendingProfile (Existing, Reused)

**Location**: `app/models/config/spending.py`

**Purpose**: Represents a time period with a specific spending amount

**Attributes**:
| Name | Type | Required | Validation | Description |
|------|------|----------|------------|-------------|
| `yearly_amount` | `int` | Yes | Positive integer | Base yearly spending in thousands |
| `end_date` | `float \| None` | No | Must be > previous profile's end_date if not last | Date when this profile ends (None for final profile) |

**Validation Rules**:
- All profiles except last must have `end_date`
- Last profile must have `end_date = None`
- Profiles must be in chronological order
- At least one profile must exist

**Relationships**:
- Owned by `InflationFollowingConfig.profiles` (1..* cardinality)

**Lifecycle**: Immutable once loaded from config

---

#### InflationFollowingConfig (New)

**Location**: `app/models/config/spending.py`

**Purpose**: Configuration for inflation-following spending strategy

**Base Class**: `StrategyConfig`

**Attributes**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `chosen` | `bool` | Yes | `True` | Inherited from StrategyConfig; marks this strategy as selected |
| `profiles` | `list[SpendingProfile]` | Yes | - | Ordered list of spending profiles |

**Validation Rules** (via `@model_validator`):
- Delegates to `_spending_profiles_validation(self.profiles)`
- Raises `ValueError` if validation fails
- Validation runs during Pydantic model construction

**Relationships**:
- Contains `profiles` (list of SpendingProfile)
- Owned by `SpendingStrategyOptions.inflation_following`

**Lifecycle**: Created during config load; immutable after validation

**Methods**:
```python
@model_validator(mode="after")
def validate_profiles(self) -> Self:
    """Validate spending profiles using existing validation logic"""
    _spending_profiles_validation(self.profiles)
    return self
```

---

#### SpendingStrategyOptions (New)

**Location**: `app/models/config/spending.py`

**Purpose**: Container for all spending strategy options

**Base Class**: `StrategyOptions`

**Attributes**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `inflation_following` | `InflationFollowingConfig` | Yes | `InflationFollowingConfig(chosen=True)` | The inflation-following strategy configuration |

**Relationships**:
- Referenced by `User.spending_strategy`
- Contains `inflation_following` (InflationFollowingConfig)

**Lifecycle**: Created during config load; immutable

**Inherited Behavior**:
- `chosen_strategy` property returns tuple of (strategy_name, strategy_config) for the chosen strategy

---

### Runtime Entities (Controllers)

#### _Strategy (Abstract Base Class) (New)

**Location**: `app/models/controllers/spending.py`

**Purpose**: Abstract interface for spending calculation strategies

**Type**: ABC (Abstract Base Class)

**Methods**:
```python
@abstractmethod
def calc_spending(self, state: State) -> float:
    """Calculate spending amount for given state
    
    Args:
        state: Current simulation state
        
    Returns:
        float: Spending amount (negative value representing outflow)
        
    Raises:
        ValueError: If no valid profile found for state.date
    """
```

**Relationships**:
- Implemented by concrete strategy classes

**Lifecycle**: Abstract - never instantiated directly

---

#### _InflationFollowingStrategy (New)

**Location**: `app/models/controllers/spending.py`

**Purpose**: Implements inflation-following spending calculation

**Type**: `@dataclass`

**Base Class**: `_Strategy`

**Attributes**:
| Name | Type | Init | Description |
|------|------|------|-------------|
| `config` | `InflationFollowingConfig` | Yes | Strategy configuration |
| `profiles` | `list[SpendingProfile]` | No (set in `__post_init__`) | Extracted profiles for fast access |

**Methods**:

```python
def __post_init__(self) -> None:
    """Extract profiles from config for efficient access"""
    self.profiles = self.config.profiles

def calc_spending(self, state: State) -> float:
    """Calculate spending using profile selection and inflation adjustment
    
    Algorithm:
    1. Iterate through profiles in order
    2. Select first profile where (end_date is None) OR (state.date <= end_date)
    3. Calculate: -yearly_amount / INTERVALS_PER_YEAR * state.inflation
    4. Return negative value (outflow)
    
    Args:
        state: Current simulation state
        
    Returns:
        float: Negative spending amount for the interval
        
    Raises:
        ValueError: If no profile matches (should never happen with valid config)
    """
```

**Relationships**:
- Contains `config` (InflationFollowingConfig)
- References `profiles` from config
- Used by `Controller`

**Lifecycle**: 
- Created once during Controller initialization
- Lives for duration of simulation trial
- Stateless (reads from State parameter)

**Invariants**:
- `profiles` is non-empty (guaranteed by config validation)
- Last profile has `end_date = None` (guaranteed by config validation)
- Profiles are chronologically ordered (guaranteed by config validation)

---

#### Controller (New)

**Location**: `app/models/controllers/spending.py`

**Purpose**: Public interface for spending calculation; manages strategy selection

**Type**: Regular class

**Attributes**:
| Name | Type | Visibility | Description |
|------|------|------------|-------------|
| `_strategy` | `_Strategy` | Private | Selected and instantiated strategy |

**Methods**:

```python
def __init__(self, user: User) -> None:
    """Initialize controller with appropriate strategy
    
    Args:
        user: User configuration containing spending_strategy
        
    Raises:
        ValueError: If invalid strategy name selected
    """
    # Extract strategy using chosen_strategy property
    # Match on strategy name to instantiate correct class
    # Store in self._strategy

def calc_spending(self, state: State) -> float:
    """Calculate spending amount for current state
    
    Delegates to the selected strategy.
    
    Args:
        state: Current simulation state
        
    Returns:
        float: Spending amount (negative value)
        
    Raises:
        ValueError: If strategy cannot calculate spending for given state
    """
    return self._strategy.calc_spending(state=state)
```

**Relationships**:
- Owns `_strategy` (instantiated strategy)
- Used by `Controllers` dataclass
- Called by `StateChangeComponents`

**Lifecycle**:
- Created once per simulation trial during `Controllers` initialization
- Lives for duration of trial
- Stateless (delegates to strategy)

**Strategy Selection Logic**:
```python
strategy_name, strategy_config = user.spending_strategy.chosen_strategy
match strategy_name:
    case "inflation_following":
        self._strategy = _InflationFollowingStrategy(
            config=cast(config.InflationFollowingConfig, strategy_config)
        )
    case _:
        raise ValueError(f"Invalid spending strategy: {strategy_name}")
```

---

#### Controllers (Updated)

**Location**: `app/models/controllers/__init__.py`

**Purpose**: Aggregates all controllers for a simulation trial

**Type**: `@dataclass`

**New Attribute**:
| Name | Type | Description |
|------|------|-------------|
| `spending` | `spending_module.Controller` | Spending calculation controller |

**Integration**: Add import and field:
```python
from . import spending as spending_module

@dataclass
class Controllers:
    # ... existing fields ...
    spending: spending_module.Controller
```

---

## Data Flow

### Configuration Load Flow

```text
1. User loads config.yml
   ↓
2. Pydantic parses User model
   ↓
3. User.spending_strategy: SpendingStrategyOptions parsed
   ↓
4. SpendingStrategyOptions.inflation_following: InflationFollowingConfig parsed
   ↓
5. InflationFollowingConfig.profiles: list[SpendingProfile] parsed
   ↓
6. @model_validator runs validate_profiles()
   ↓
7. Validation passes OR raises ValueError
   ↓
8. User object ready for simulation
```

### Controller Initialization Flow

```text
1. Simulation creates Controllers dataclass
   ↓
2. Controllers.__init__ instantiates spending.Controller(user)
   ↓
3. Controller.__init__ calls user.spending_strategy.chosen_strategy
   ↓
4. Gets ("inflation_following", InflationFollowingConfig instance)
   ↓
5. Match on "inflation_following"
   ↓
6. Instantiates _InflationFollowingStrategy(config)
   ↓
7. __post_init__ extracts profiles from config
   ↓
8. Controller ready with _strategy set
```

### Spending Calculation Flow

```text
1. StateChangeComponents._gen_costs() calls controllers.spending.calc_spending(state)
   ↓
2. Controller.calc_spending(state) delegates to self._strategy.calc_spending(state)
   ↓
3. _InflationFollowingStrategy.calc_spending(state):
   a. Iterate through self.profiles
   b. Find first profile where (end_date is None) OR (state.date <= end_date)
   c. Calculate: -profile.yearly_amount / INTERVALS_PER_YEAR * state.inflation
   d. Return negative float
   ↓
4. Value returned to StateChangeComponents
   ↓
5. Used in _Costs calculation
```

## State Transitions

### SpendingProfile State

**States**: None (immutable value object)

### InflationFollowingConfig State

**States**: None (immutable after validation)

### Controller State

**States**: None (stateless - delegates to strategy)

### _InflationFollowingStrategy State

**States**: None (stateless - pure calculation based on input State)

## Validation Rules Summary

| Entity | Validation | When | Error Message |
|--------|------------|------|---------------|
| SpendingProfile | (Part of list validation) | Config load | (See below) |
| InflationFollowingConfig | `_spending_profiles_validation` | Pydantic validation | "All spending profiles except the last must have an end_date" |
| | | | "Spending profiles must be in order" |
| | | | "Last spending profile should have no end date" |
| | Empty list | Pydantic validation | (Pydantic default: field required) |
| Controller | Invalid strategy name | Initialization | "Invalid spending strategy: {name}" |
| _InflationFollowingStrategy | No matching profile | calc_spending() | "No spending profile found for the current date" |

## Type Signatures Summary

```python
# Config types
SpendingProfile: BaseModel
    yearly_amount: int
    end_date: float | None

InflationFollowingConfig: StrategyConfig
    chosen: bool
    profiles: list[SpendingProfile]

SpendingStrategyOptions: StrategyOptions
    inflation_following: InflationFollowingConfig

# Controller types
_Strategy: ABC
    calc_spending(state: State) -> float

_InflationFollowingStrategy: _Strategy, dataclass
    config: InflationFollowingConfig
    profiles: list[SpendingProfile] (field(init=False))
    calc_spending(state: State) -> float

Controller:
    _strategy: _Strategy
    __init__(user: User) -> None
    calc_spending(state: State) -> float
```

## Dependencies

```text
Config Layer:
  app.models.config.spending
    ↓ imports
  app.models.config.strategy (StrategyConfig, StrategyOptions)
    ↓ uses
  pydantic (BaseModel, Field, model_validator)

Controller Layer:
  app.models.controllers.spending
    ↓ imports
  app.models.config (for type hints)
  app.models.config.spending (InflationFollowingConfig)
  app.models.financial.state (State)
  app.data.constants (INTERVALS_PER_YEAR)
    ↓ uses
  abc, dataclasses, typing

Integration:
  app.models.controllers.__init__
    ↓ imports
  app.models.controllers.spending
    ↓ uses in
  Controllers dataclass

  app.models.financial.state_change
    ↓ uses
  controllers.spending.calc_spending()
```

## Migration Notes

### Breaking Changes

1. **Config Format**: `User.spending` becomes `User.spending_strategy`
2. **Structure**: Profiles move from `spending.profiles` to `spending_strategy.inflation_following.profiles`

### Migration Path (NOT IMPLEMENTED - Out of Scope)

Users must manually update their config files to the new format.

Example transformation:
```yaml
# OLD (will break)
spending:
  spending_strategy:
    inflation_only:
      chosen: true
  profiles:
    - yearly_amount: 60
      end_date: 2035.25

# NEW (required)
spending_strategy:
  inflation_following:
    chosen: true
    profiles:
      - yearly_amount: 60
        end_date: 2035.25
```

