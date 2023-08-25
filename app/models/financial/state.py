"""Module for representing financial state at instance in time

Classes:
    State: Dataclass that captures a user's financial state at a given date

Methods:
    gen_first_state(user: User): Create initial state given a user
"""

from dataclasses import dataclass
from app.data import constants
from app.models.config import User


@dataclass
class State:
    """
    Attributes
        user (User)

        date (float)

        interval_idx (int)

        net_worth (float)

        inflation (float)
    """

    user: User
    date: float
    interval_idx: int
    net_worth: float
    inflation: float


def gen_first_state(user: User):
    """Create initial state given a user"""
    return State(
        user=user,
        date=constants.TODAY_YR_QT,
        interval_idx=0,
        net_worth=user.portfolio.current_net_worth,
        inflation=1,
    )
