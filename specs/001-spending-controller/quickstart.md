# Quickstart: Spending Controller

**Feature**: 001-spending-controller  
**Audience**: Developers implementing or using the spending controller  
**Last Updated**: 2026-01-01

## Overview

The spending controller calculates spending amounts for each simulation interval using a strategy-based architecture. Currently, only the `inflation_following` strategy is implemented, which selects spending profiles based on date and applies inflation adjustment.

## Quick Reference

### Configuration Format

```yaml
spending_strategy:
  inflation_following:
    chosen: true
    profiles:
      - yearly_amount: 60      # $60K/year
        end_date: 2035.25      # Through Q1 2035
      - yearly_amount: 70      # $70K/year
        end_date: 2040.25      # Through Q1 2040
      - yearly_amount: 55      # $55K/year forever
        # No end_date = continues indefinitely
```

### Using the Controller

```python
from app.models.controllers import Controllers
from app.models.financial.state import State

# Controller is created as part of Controllers initialization
controllers = Controllers(
    # ... other controllers ...
    spending=spending_module.Controller(user=user),
    # ... other controllers ...
)

# Calculate spending for current state
spending_amount = controllers.spending.calc_spending(state=current_state)
# Returns: negative float (e.g., -15.75 for $15.75K outflow in one quarter)
```

### Key Behaviors

| Scenario | Behavior |
|----------|----------|
| **Date on boundary** | Profile remains active through its end_date (e.g., profile with end_date 2035.25 is active when state.date = 2035.25) |
| **Zero inflation** | Spending = base amount (inflation multiplier of 0.0 is applied) |
| **Negative inflation** | Spending reduced (deflation applied as-is) |
| **Empty profiles** | **Error** at config load (Pydantic validation) |
| **Last profile with end_date** | **Error** at config load (validation) |
| **Out-of-order profiles** | **Error** at config load (validation) |

## Configuration Details

### SpendingProfile

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `yearly_amount` | `int` | ✓ | Positive integer (thousands) |
| `end_date` | `float \| None` | Only for non-final profiles | Must be > previous profile's end_date |

**Validation Rules**:
- At least one profile required
- All profiles except last must have `end_date`
- Last profile must have `end_date = None`
- Profiles must be in chronological order

### InflationFollowingConfig

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `chosen` | `bool` | ✓ | `true` |
| `profiles` | `list[SpendingProfile]` | ✓ | - |

## Implementation Patterns

### Adding a New Strategy (Future)

1. **Create strategy config class** in `app/models/config/spending.py`:
   ```python
   class NewStrategyConfig(StrategyConfig):
       chosen: bool = False
       # ... strategy-specific fields ...
   ```

2. **Add to SpendingStrategyOptions**:
   ```python
   class SpendingStrategyOptions(StrategyOptions):
       inflation_following: InflationFollowingConfig = ...
       new_strategy: NewStrategyConfig = NewStrategyConfig()
   ```

3. **Implement strategy class** in `app/models/controllers/spending.py`:
   ```python
   @dataclass
   class _NewStrategy(_Strategy):
       config: NewStrategyConfig
       
       def calc_spending(self, state: State) -> float:
           # Implementation
           pass
   ```

4. **Add case to Controller match statement**:
   ```python
   match strategy_name:
       case "inflation_following":
           # ...
       case "new_strategy":
           self._strategy = _NewStrategy(
               config=cast(config.NewStrategyConfig, strategy_config)
           )
   ```

### Testing Patterns

#### Unit Test: Strategy

```python
def test_inflation_following_strategy():
    config = InflationFollowingConfig(
        chosen=True,
        profiles=[
            SpendingProfile(yearly_amount=60, end_date=2035.0),
            SpendingProfile(yearly_amount=55, end_date=None),
        ]
    )
    strategy = _InflationFollowingStrategy(config=config)
    
    state = State(date=2030.0, inflation=1.05, ...)
    result = strategy.calc_spending(state=state)
    
    expected = -60 / 4 * 1.05  # -15.75
    assert result == pytest.approx(expected)
```

#### Integration Test: Controller

```python
def test_spending_controller_integration(sample_user_with_spending):
    controller = Controller(user=sample_user_with_spending)
    state = State(date=2030.0, inflation=1.05, ...)
    
    spending = controller.calc_spending(state=state)
    
    assert spending < 0  # Negative (outflow)
    assert abs(spending) > 0  # Non-zero
```

#### Validation Test: Config

```python
def test_spending_config_validation_empty_profiles():
    with pytest.raises(ValidationError):
        InflationFollowingConfig(chosen=True, profiles=[])

def test_spending_config_validation_last_profile_has_end_date():
    with pytest.raises(ValueError, match="Last spending profile should have no end date"):
        InflationFollowingConfig(
            chosen=True,
            profiles=[
                SpendingProfile(yearly_amount=60, end_date=2035.0),  # Wrong!
            ]
        )
```

## Calculation Formula

```
spending = -(yearly_amount / INTERVALS_PER_YEAR) * inflation
```

Where:
- `yearly_amount`: From active SpendingProfile
- `INTERVALS_PER_YEAR`: Constant = 4 (quarterly intervals)
- `inflation`: From State object (cumulative inflation multiplier)
- Negative sign: Represents cash outflow

**Example**:
- Profile: `yearly_amount = 60` ($60K/year)
- Inflation: `1.05` (5% cumulative)
- Calculation: `-(60 / 4) * 1.05 = -15.75`
- Result: $15.75K spent in this quarter

## Profile Selection Algorithm

```python
for profile in profiles:
    if profile.end_date is None or state.date <= profile.end_date:
        # This profile is active
        return calculate_spending_from(profile, state.inflation)

# Should never reach here if config is valid
raise ValueError("No spending profile found for the current date")
```

**Key Points**:
- Iterates profiles in order (chronological)
- First match wins
- Profile with `end_date = None` always matches (catch-all)
- Boundary behavior: `date <= end_date` means profile active through end_date

## Common Errors and Solutions

### Configuration Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "All spending profiles except the last must have an end_date" | Non-final profile missing end_date | Add end_date to all profiles except the last |
| "Last spending profile should have no end date" | Final profile has end_date | Remove end_date from last profile (or set to null) |
| "Spending profiles must be in order" | Profiles out of chronological order | Sort profiles by end_date (ascending) |
| Field required (Pydantic) | Empty profiles list | Add at least one spending profile |

### Runtime Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "No spending profile found for the current date" | Simulation date beyond all profiles AND last profile has end_date | Should never happen if validation works; check config validation |
| "Invalid spending strategy: {name}" | Unknown strategy name in config | Use "inflation_following" or add new strategy implementation |

## Migration from Old Format

### Old Format (No Longer Supported)
```yaml
spending:
  spending_strategy:
    inflation_only:
      chosen: true
  profiles:
    - yearly_amount: 60
      end_date: 2035.25
```

### New Format (Required)
```yaml
spending_strategy:
  inflation_following:
    chosen: true
    profiles:
      - yearly_amount: 60
        end_date: 2035.25
```

**Changes**:
1. Move `spending_strategy` to root level
2. Rename `inflation_only` → `inflation_following`
3. Move `profiles` inside `inflation_following`
4. Remove `spending` wrapper

**Note**: No automatic migration tool provided. Users must manually update configs.

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Controller creation | O(1) | One strategy instantiated |
| calc_spending() | O(n) where n = # profiles | Linear scan, typically n = 2-5 |
| Profile validation | O(n²) | During config load only |

**Typical Performance**:
- `calc_spending()`: <0.01ms per call
- Profiles typically 2-5 in number
- No memory allocation during calculation

## Dependencies

```text
Controllers (runtime)
├── spending.Controller
    ├── _InflationFollowingStrategy
    │   ├── InflationFollowingConfig
    │   │   └── list[SpendingProfile]
    │   └── State (parameter)
    └── User.spending_strategy

State (parameter)
├── date: float
├── inflation: float
└── user: User
```

## Related Documentation

- **Specification**: `specs/001-spending-controller/spec.md`
- **Data Model**: `specs/001-spending-controller/data-model.md`
- **Research**: `specs/001-spending-controller/research.md`
- **Allocation Controller** (similar pattern): `app/models/controllers/allocation.py`
- **Constitution**: `.specify/memory/constitution.md` (testing & code quality standards)

