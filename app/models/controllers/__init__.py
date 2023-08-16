"""Modules whose information is used by all intervals in a trial

Classes:
    Controllers: All controllers used by a simulation trial
"""
from dataclasses import dataclass
from . import (
    allocation as allocation_module,
    economic_data as economic_data_module,
    job_income as job_income_module,
    # social_security as social_security_module,
    # annuity as annuity_module,
    # pension as pension_module,
)


@dataclass
class Controllers:
    """All controllers used by a simulation trial

    Attributes:
        allocation (allocation.Controller): Manages strategy and allocation generation

        economic_data (economic_data.Controller): Manages trial economic data

        job_income (job_income.Controller): Manages job income timelines
    """

    allocation: allocation_module.Controller = None
    economic_data: economic_data_module.Controller = None
    job_income: job_income_module.Controller = None
    # social_security: social_security_module.Controller = None
    # annuity: annuity_module.Controller = None
    # pension: pension_module.Controller = None
