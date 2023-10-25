"""Model of social security.

Classes:
    Controller: Generate and provide social security payments
"""
import math
from abc import ABC, abstractmethod
from app.util import index_extrapolator, max_earnings_extrapolator
from app.data import constants
from app.models.financial.state import State
from app.models.config import NetWorthStrategyConfig, SocialSecurity, User
from app.models.controllers.job_income import Income, Controller as IncomeController

EARLY_AGE = 62
MID_AGE = 66
LATE_AGE = 70


def _gen_earnings(timeline: list[Income], earnings_record: dict) -> list[float]:
    """Generate a list of valid earnings.

    Args:
        timeline (list[Income]): A list of Income objects in sequential order.
        earnings_record (dict): Historical record of earnings {year:income}

    Returns:
        list[float]: Valid earnings adjusted for social security maxes and indices
    """
    filled_timeline = _fill_in_missing_intervals(timeline)
    eligible_timeline = list(
        filter(lambda income: income.social_security_eligible, filled_timeline)
    )
    _add_income_to_earnings_record(
        timeline=eligible_timeline, earnings_record=earnings_record
    )
    return _constrain_earnings(earnings_record)


def _fill_in_missing_intervals(timeline: list[Income]) -> list[Income]:
    """Create a timeline that starts and ends on a new year.

    Social security doesn't measure income in intervals, so the timeline
    needs to be adjusted to start and end on a new year. This function
    creates a new timelines with extra Income objects at the beginning
    and end if needed to make sure the timeline starts and ends on a new year.

    Args:
        timeline (list[Income]): original timeline

    Returns:
        list[Income]: new timeline object that begins and ends on new year
    """
    timeline_copy = timeline.copy()  # don't mutate original
    while not math.isclose(timeline_copy[0].date % 1, 0):
        # insert new Income objects at the beginning of timeline
        timeline_copy.insert(
            0,
            Income(
                date=timeline_copy[0].date - constants.YEARS_PER_INTERVAL,
                amount=timeline_copy[0].amount,
                tax_deferred=timeline_copy[0].tax_deferred,
                try_to_optimize=timeline_copy[0].try_to_optimize,
                social_security_eligible=timeline_copy[0].social_security_eligible,
            ),
        )
    while not math.isclose(timeline_copy[-1].date % 1, 0.75):
        # insert new Income objects at the end of timeline till a date ends with .75
        timeline_copy.append(
            Income(
                date=timeline_copy[-1].date + constants.YEARS_PER_INTERVAL,
                amount=timeline_copy[-1].amount,
                tax_deferred=timeline_copy[-1].tax_deferred,
                try_to_optimize=timeline_copy[-1].try_to_optimize,
                social_security_eligible=timeline_copy[-1].social_security_eligible,
            ),
        )
    return timeline_copy


def _add_income_to_earnings_record(timeline: list[Income], earnings_record: dict):
    """Timeline income is added to the earnings record.

    `timeline` is expected to have length of `intervals_per_trial`,
    with fractional dates for each interval. The income for each
    interval is added to the earnings record for the year of the
    interval.

    Args:
        timeline (list[Income]): timeline from income controller
        earnings_record (dict): historical record of earnings {year:income}
        Defaults to self._earnings_record.
    """
    for income in timeline:
        year = math.trunc(income.date)
        if income.amount != 0:
            if year in earnings_record:
                earnings_record[year] += income.amount
            else:
                earnings_record[year] = income.amount


def _constrain_earnings(earnings_record: dict):
    """Constrain earnings to max earnings and mutiply by index.

    Earnings over the max earnings cannot be used to calculate the PIA.
    The index adjusts the earnings to today's dollars.

    Args:
        earnings_record (dict): {year:earning}.

    Returns:
        list[float]: Valid earnings
    """
    return [
        min(max_earnings_extrapolator(year), earning) * index_extrapolator(year)
        for year, earning in earnings_record.items()
    ]


def _gen_pia(earnings: list, ss_config: SocialSecurity) -> float:
    """Generate the Primary Insurance Amount (PIA).

    Args:
        earnings (list): Valid earnings.

    Returns:
        float: PIA
    """
    aime = _calc_aime(earnings)
    bend_points = _adjust_bend_points(aime)
    return _apply_pia_rates(bend_points=bend_points, ss_config=ss_config)


def _calc_aime(earnings: list) -> float:
    """Calculate Average Indexed Monthly Earnings (AIME)

    AIME is the average of the top 35 years of earnings,
    including years with zero income

    Args:
        earnings (list): List of all yearly eligible earnings.

    Returns:
        float: AIME
    """
    earnings.sort(reverse=True)
    return sum(earnings[:35]) / 420


def _adjust_bend_points(aime: float) -> list[float]:
    """Adjust official bend points to include AIME.

    Bends Points are the AIME values at which the PIA rates change. This
    rate is multiplied by the income between the bend points to calculate
    the PIA.

    Example (bends points and rates change every year)
    Bend Point    |    PIA Rate     |   Cumulative PIA
    --------------------------------------------------
        $996       |      90%        |       $896.40

        $6,002     |      32%        |       $2,498.32

        $8,000*    |      15%        |       $2,798.02

    *The third 'bend point' is just the AIME if it's larger than
    the second bend point.

    This function adjusts the official bend points be the minimum of
    the AIME and next largest offical bend point. For example, if the
    AIME is $4,500, the resulting bend points will be [996, 4500].

    Args:
        aime (float): _description_

    Returns:
        list[float]: _description_
    """
    bend_points = constants.SS_BEND_POINTS + [aime]
    bend_points.sort()
    # cut off bend points at inserted AIME
    return bend_points[: bend_points.index(aime) + 1]


def _apply_pia_rates(bend_points: list[float], ss_config: SocialSecurity) -> float:
    """Apply PIA rates to bend points to calculate PIA.

    Bends Points are the AIME values at which the PIA rates change. This
    rate is multiplied by the income between the bend points to calculate
    the PIA.

    Example (bends points and rates change every year)
    Bend Point    |    PIA Rate     |   Cumulative PIA
    --------------------------------------------------
        $996       |      90%        |       $896.40

        $6,002     |      32%        |       $2,498.32

        $8,000*    |      15%        |       $2,798.02

    *The third 'bend point' is just the AIME if it's larger than
    the second bend point. When passing in bend points, the final
    bend point should be the minimum of the AIME and next largest
    offical bend point. For example, if the AIME is $4,500, the passed
    in `bend_points` should be [996, 4500].

    Args:
        bend_points (list[float]): generated bend_points given AIME

        ss_config (SocialSecurity)

    Returns:
        float: Calculated PIA
    """
    if ss_config.pension_eligible:
        pia_rates = constants.PIA_RATES_PENSION
    else:
        pia_rates = constants.PIA_RATES
    pia = 0
    for (i, bend), rate in zip(enumerate(bend_points), pia_rates):
        if i == 0:
            pia += bend * rate
        else:
            pia += (bend_points[i] - bend_points[i - 1]) * rate
    return pia


class _Strategy(ABC):
    """Abstract allocation strategy class.

    Required properties:
        trigger_date (float): Date when social security is started

        benefit_rate (float): Rate at which PIA is multiplied to calculate payment

    Required methods:
        calc_payment(self, state: State) -> float:
    """

    @property
    @abstractmethod
    def trigger_date(self):
        """Date when social security is started"""

    @property
    @abstractmethod
    def benefit_rate(self):
        """Rate at which PIA is multiplied to calculate payment"""

    @abstractmethod
    def calc_payment(self, state: State) -> float:
        """Calculate social security payment based on current state

        Args:
            state (State): current state

        Returns:
            float: social security payment for interval
        """


class _AgeStrategy(_Strategy):
    def __init__(self, pia: float, ss_age: int, current_age: int):
        self._trigger_date = ss_age - current_age + constants.TODAY_YR + 1
        self._benefit_rate: float = constants.BENEFIT_RATES[ss_age]
        self._adjusted_pia = pia * self.benefit_rate

    @property
    def trigger_date(self):
        return self._trigger_date

    @property
    def benefit_rate(self):
        return self._benefit_rate

    def calc_payment(self, state: State) -> float:
        if state.date < self.trigger_date:
            return 0
        return constants.MONTHS_PER_INTERVAL * self._adjusted_pia * state.inflation


class _NetWorthStrategy(_Strategy):
    def __init__(self, config: NetWorthStrategyConfig, pia: float, current_age: int):
        self._trigger_date = float("inf")
        self._benefit_rate = 0
        self._net_worth_target = config.net_worth_target
        self._pia = pia
        self._current_age = current_age
        self._adjusted_pia = 0

    @property
    def trigger_date(self):
        return self._trigger_date

    @trigger_date.setter
    def trigger_date(self, value):
        self._trigger_date = value

    @property
    def benefit_rate(self):
        return self._benefit_rate

    @benefit_rate.setter
    def benefit_rate(self, value):
        self._benefit_rate = value

    def calc_payment(self, state: State) -> float:
        if state.date >= self.trigger_date:  # already triggered
            return constants.MONTHS_PER_INTERVAL * self._adjusted_pia * state.inflation
        age_at_state = self._current_age + math.trunc(state.date) - constants.TODAY_YR
        if age_at_state < EARLY_AGE:  # too young
            return 0
        if (
            age_at_state == LATE_AGE
            or state.net_worth < self._net_worth_target * state.inflation
        ):
            self.benefit_rate = constants.BENEFIT_RATES[age_at_state]
            self._adjusted_pia = self._pia * self.benefit_rate
            self.trigger_date = state.date
            return constants.MONTHS_PER_INTERVAL * self._adjusted_pia * state.inflation
        return 0


class _IndividualController:
    def __init__(self, ss_config: SocialSecurity, timeline: list[Income], age: int):
        """
        Controller should initially create a state compatiable will all strategies
        Strategies all need to cover the same level of scope, so though
        early, mid, and late shouldn't have to calculate the payment, since net_worth
        will, they need to as well.

        Generate earnings:
            - Generate earnings record from config
            - Calculate eligible income
            - Add eligible income to earnings record
        Calculate PIA:
            - Calculate AIME
            - Apply bend points
            - Apply PIA rates
        Create strategy
        ----Remaining is handled by strategies----
        - Adjust PIA
        - Calculate payment

        Methods:
            calc_payment(self, state: State) -> float: Calculate social security payment
        """
        earnings_record = ss_config.earnings_records.copy()
        valid_earnings = _gen_earnings(
            timeline=timeline, earnings_record=earnings_record
        )
        if valid_earnings:
            self.pia = _gen_pia(earnings=valid_earnings, ss_config=ss_config)
        else:
            self.pia = 0

        (
            strategy_str,
            strategy_obj,
        ) = ss_config.strategy.chosen_strategy
        match strategy_str:
            case "early":
                self.strategy = _AgeStrategy(
                    pia=self.pia, ss_age=EARLY_AGE, current_age=age
                )
            case "mid":
                self.strategy = _AgeStrategy(
                    pia=self.pia, ss_age=MID_AGE, current_age=age
                )
            case "late":
                self.strategy = _AgeStrategy(
                    pia=self.pia, ss_age=LATE_AGE, current_age=age
                )
            case "net_worth":
                self.strategy = _NetWorthStrategy(
                    config=strategy_obj, pia=self.pia, current_age=age
                )

    def calc_payment(self, state: State):
        """Get the social security payment for the current state.

        Args:
            state (State)

        Returns:
            float: payment
        """
        return self.strategy.calc_payment(state)


def _calc_spousal_benefit(
    worker_controller: _IndividualController,
    spousal_controller: _IndividualController,
    state: State,
):
    """Returns the eligible portion of a spouse's income the worker could receive.
    https://www.ssa.gov/benefits/retirement/planner/applying7.html"""
    if (
        state.date < spousal_controller.strategy.trigger_date
        or state.date < worker_controller.strategy.trigger_date
    ):
        # if spouse not receiving payments yet or worker's social security
        # hasn't been triggered yet (worker's SS strategy should not be overridden
        # by spouse's strategy)
        return 0
    spouse_pia = spousal_controller.pia
    # Worker's can earn up to half of their spouse's PIA, adjusted by the worker's benefit rate
    spousal_benefit = 0.5 * spouse_pia * worker_controller.strategy.benefit_rate
    return spousal_benefit * constants.MONTHS_PER_INTERVAL * state.inflation


class Controller:
    """Manages strategy and payment generation

    Methods
        calc_payment(self, state: State) -> float:
        Calculate total social security payment for the current state
    """

    def __init__(self, user_config: User, income_controller: IncomeController):
        self._user_controller = _IndividualController(
            ss_config=user_config.social_security_pension,
            timeline=income_controller._user_timeline,
            age=user_config.age,
        )
        if user_config.partner is None:
            self._partner_controller = None
        else:
            if (
                user_config.partner.social_security_pension.strategy.chosen_strategy[0]
                == "same"
            ):
                partner_config = user_config.social_security_pension
            else:
                partner_config = user_config.partner.social_security_pension
            self._partner_controller = _IndividualController(
                ss_config=partner_config,
                timeline=income_controller._partner_timeline,
                age=user_config.partner.age,
            )

    def calc_payment(self, state: State) -> tuple[float, float]:
        """Calculate total social security payment for the current state.

        Return the sum of the user's and partner's social security payments.
        Each one's payments are compared to their spousal benefit before
        returning the higher of the two.

        Args:
            state (State): current state

        Returns:
            tuple[float, float] : user payment, partner payment
        """
        user_payment = self._user_controller.calc_payment(state)
        if self._partner_controller is None:
            partner_payment = 0
        else:
            users_spousal_benefit = _calc_spousal_benefit(
                worker_controller=self._user_controller,
                spousal_controller=self._partner_controller,
                state=state,
            )
            if users_spousal_benefit > user_payment:
                user_payment = users_spousal_benefit
            partner_payment = self._partner_controller.calc_payment(state)
            partners_spousal_benefit = _calc_spousal_benefit(
                worker_controller=self._partner_controller,
                spousal_controller=self._user_controller,
                state=state,
            )
            if partners_spousal_benefit > partner_payment:
                partner_payment = partners_spousal_benefit
        return user_payment, partner_payment
