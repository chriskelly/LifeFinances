"""Profile total portfolio allocation strategy performance.

Run from specs directory: make profile

This profiles:
1. Strategy initialization (__post_init__)
2. Allocation generation (gen_allocation) across multiple intervals
3. Present value calculation (NPV)
4. Income array precomputation

Expected performance targets:
- Allocation calculation: <1ms per interval
- Present value calculation: <10ms per interval
"""

import sys
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml

from app.models.config import User
from app.models.simulator import SimulationEngine


def profile_total_portfolio_allocation():
    """Profile total portfolio allocation strategy with realistic configuration."""
    # Load a config with total portfolio strategy
    config_path = (
        Path(__file__).parent.parent.parent
        / "tests"
        / "sample_configs"
        / "full_config.yml"
    )
    with open(config_path, encoding="utf-8") as file:
        config_data = yaml.safe_load(file)

    assert config_data is not None, "Failed to load config"
    assert isinstance(config_data, dict), "Config is not a dict"

    # Modify to use total_portfolio strategy
    config_data["portfolio"]["allocation_strategy"]["total_portfolio"]["chosen"] = True
    config_data["portfolio"]["allocation_strategy"]["flat"]["chosen"] = False

    # Save temporary config for profiling
    temp_config_path = Path(__file__).parent / "temp_profile_config.yml"
    with open(temp_config_path, "w", encoding="utf-8") as file:
        yaml.dump(config_data, file)

    # Validate config
    user = User(**config_data)  # type: ignore[arg-type]

    # Run a full simulation to profile allocation across all intervals
    engine = SimulationEngine(config_path=temp_config_path, trial_qty=100)
    engine.gen_all_trials()

    # Clean up temp config
    temp_config_path.unlink()

    print("✓ Profiling complete")
    print(f"  Trials: {engine._trial_qty}")
    print(f"  Intervals per trial: {user.intervals_per_trial}")
    print(
        f"  Total allocation calculations: {engine._trial_qty * user.intervals_per_trial}"
    )


if __name__ == "__main__":
    profile_total_portfolio_allocation()
