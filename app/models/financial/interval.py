"""Financial intervals represent a single period of time in a user's financial life

The include a State and a StateChangeComponents. The StateChangeComponents is used to generate
the state of the subsequent Interval.

Classes:
    Interval: A single period of time in a user's financial life

Methods:
    gen_first_interval(trial: SimulationTrial): 
"""
from app.models.config import User
from app.models.controllers import Controllers
from app.models.financial.state import State, gen_first_state
from app.models.financial.state_change import StateChangeComponents


class Interval:
    """A single period of time in a user's financial life
    Attributes
        state (State)

    Methods
        gen_next_interval(): Generate the next interval from State + Transformation
    """

    def __init__(self, state: State, controllers: Controllers):
        self.state = state
        self.state_change_components = StateChangeComponents(state, controllers)

    def gen_next_interval(self):
        """Generate the next interval from State + StateChangeComponents"""


def gen_first_interval(user_config: User, controllers: Controllers):
    """Generate the first interval of a trial from the user config"""
    state = gen_first_state(user_config)
    return Interval(state, controllers)
