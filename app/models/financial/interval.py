"""Financial intervals represent a single period of time in a user's financial life

The include a State and a Transformation. The Transformation is used to generate
the state of the subsequent Interval.

Classes:
    Interval: A single period of time in a user's financial life

Methods:
    gen_first_interval(user: User): 
"""
from app.models.config import get_config
from app.models.financial.state import State, gen_first_state

# from app.models.financial.transformation import Transformation
# from app.data import constants as const


class Interval:
    """A single period of time in a user's financial life
    Attributes
        state (State)

    Methods
        gen_next_interval(): Generate the next interval from State + Transformation
    """

    def __init__(self, state: State):
        self.state = state
        # self.transformation = self._gen_transformation()

    # def _gen_transformation(self) -> Transformation:
    #     def income_from_income_groups(state: State):
    #         pass

    #     def spending(state: State):
    #         pass

    #     def econ_data(date: float):
    #         pass

    #     return Transformation(
    #         total_income=income_from_income_groups(self.state),
    #         total_costs=spending(self.state),
    #         economic_data=econ_data(self.state.date),
    #         allocation=None,
    #     )

    def gen_next_interval(self):
        """Generate the next interval from State + Transformation"""


def gen_first_interval():
    """Generate the first interval of a trial from the user config"""
    state = gen_first_state(get_config())
    return Interval(state)
