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

        state_change_components (StateChangeComponents)

    Methods
        gen_next_interval(): Generate the next interval from State + Transformation
    """

    def __init__(self, state: State, controllers: Controllers):
        self.state = state
        self.state_change_components = StateChangeComponents(state, controllers)

    def gen_next_interval(self, controllers: Controllers):
        """Generate the next interval from State + StateChangeComponents"""
        next_state = State(
            user=self.state.user,
            date=self.state.date + 0.25,
            interval_idx=self.state.interval_idx + 1,
            net_worth=self.state.net_worth
            + self.state_change_components.net_transactions,
            inflation=self.state.inflation,  #! Figure out next inflation
            working=self.state.working,  #! Figure out next working
        )
        return type(self)(state=next_state, controllers=controllers)


def gen_first_interval(user_config: User, controllers: Controllers):
    """Generate the first interval of a trial from the user config"""
    state = gen_first_state(user_config)
    return Interval(state, controllers)
