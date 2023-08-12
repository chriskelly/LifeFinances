"""Modules whose information is used by all intervals in a trial

Classes:
    Controllers: All controllers used by a simulation trial
"""
from dataclasses import dataclass
from . import allocation as allocation_module


@dataclass
class Controllers:
    """All controllers used by a simulation trial

    Attributes:
        allocation (allocation.Controller):
    """

    allocation: allocation_module.Controller = None
