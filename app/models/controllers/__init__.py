"""Modules whose information is used by all intervals in a trial

Classes:
    Controllers: All controllers used by a simulation trial
"""
from dataclasses import dataclass
from . import allocation as allocation_module, economic_data as economic_data_module


@dataclass
class Controllers:
    """All controllers used by a simulation trial

    Attributes:
        allocation (allocation.Controller): Manages strategy and allocation generation

        economic_data (economic_data.Controller): Manages trial economic data
    """

    allocation: allocation_module.Controller = None
    economic_data: economic_data_module.Controller = None
