"""Config module - re-exports all classes and functions for backward compatibility"""

# Import order matters: base classes first, then dependent classes

# Constants
# Admin (includes Pension)
from app.models.config.admin import Admin, Pension, PensionOptions

# Benefits (Social Security)
from app.models.config.benefits import (
    NetWorthStrategyConfig,
    SocialSecurity,
    SocialSecurityOptions,
)

# Income
from app.models.config.income import IncomeProfile, _income_profiles_in_order

# Kids
from app.models.config.kids import Kids

# Portfolio
from app.models.config.portfolio import (
    ALLOWED_ASSETS,
    AllocationOptions,
    AnnuityConfig,
    FlatAllocationStrategyConfig,
    NetWorthPivotStrategyConfig,
    Portfolio,
)

# Spending
from app.models.config.spending import (
    Spending,
    SpendingOptions,
    SpendingProfile,
    _spending_profiles_validation,
)

# Standalone tools
from app.models.config.standalone_tools import (
    DisabilityCoverage,
    DisabilityInsuranceCalculator,
    TPAWPlanner,
)

# Base strategy classes
from app.models.config.strategy import StrategyConfig, StrategyOptions

# User (includes Partner)
from app.models.config.user import Partner, User

# Utils
from app.models.config.utils import (
    attribute_filler,
    get_config,
    read_config_file,
    write_config_file,
)

__all__ = [
    # Constants
    "ALLOWED_ASSETS",
    # Base strategy classes
    "StrategyConfig",
    "StrategyOptions",
    # Portfolio
    "AllocationOptions",
    "AnnuityConfig",
    "FlatAllocationStrategyConfig",
    "NetWorthPivotStrategyConfig",
    "Portfolio",
    # Benefits
    "NetWorthStrategyConfig",
    "SocialSecurity",
    "SocialSecurityOptions",
    # Spending
    "Spending",
    "SpendingOptions",
    "SpendingProfile",
    "_spending_profiles_validation",
    # Income
    "IncomeProfile",
    "_income_profiles_in_order",
    # Kids
    "Kids",
    # Standalone tools
    "DisabilityCoverage",
    "DisabilityInsuranceCalculator",
    "TPAWPlanner",
    # Admin
    "Admin",
    "Pension",
    "PensionOptions",
    # User
    "Partner",
    "User",
    # Utils
    "attribute_filler",
    "get_config",
    "read_config_file",
    "write_config_file",
]
