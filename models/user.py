"""Module for representing User object and SQL table structure

This module defines the attributes of a user and the default values populated into the database.

"""
from sqlalchemy import Column, Float, ForeignKey, Integer, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

class SuperColumn(Column): # pylint: disable=abstract-method # not intending to overwrite
    """Stores additional information in the Column objects defined for each table"""
    def __init__(self, *args, label_text:str, help_text:str, **kwargs):
        """Stores additional information in the Column objects defined for each table

        Args:
            label_text (str): Human friendly label to be shown
            help_text (str): Text description of item
        
        Kwargs:
            options (iterable): Limited options for Column
            optimizable (bool): Indicates attribute can be modified by the optimizer script
        """
        self.label_text = label_text
        self.help_text = help_text
        self.options = kwargs.pop('options', [])
        self.optimizable:bool = kwargs.pop('optimizable', False)
        super().__init__(*args, **kwargs)

Base = declarative_base()

class EarningsRecord(Base):
    """A record of income earnings for a specific year

    Earnings are expected to be from the Social Security Administration, and these
    will be used to calculate social security payments.

    Args:
        Base : sqlalchemy declarative_base()
    
    Attributes: details found in `data/param_details.json`
    """
    __tablename__ = 'earnings_records'
    earnings_id:int = Column(Integer, primary_key=True, autoincrement=True)
    user_id:int = Column(ForeignKey('users.user_id'), nullable=False, server_default=text("1"))
    is_partner_earnings:bool = Column(Integer, nullable=False, server_default=text("0"))
    year:int = Column(Integer, nullable=False, server_default=text("0"))
    earnings:float = Column(Float, nullable=False, server_default=text("0"))


class JobIncome(Base):
    """Represents total income earned by individual during specific period of time

    Args:
        Base : sqlalchemy declarative_base()

    Attributes: details found in `data/param_details.json`
    """
    __tablename__ = 'job_incomes'
    job_income_id:int = Column(Integer, primary_key=True, autoincrement=True)
    starting_income:float = Column(Float, nullable=False, server_default=text("50"))
    tax_deferred_income:float = Column(Float, nullable=False, server_default=text("10"))
    last_date:float = Column(Float, nullable=False, server_default=text("2035.25"))
    yearly_raise:float = Column(Float, nullable=False, server_default=text("0.04"))
    try_to_optimize:bool = Column(Integer, nullable=False, server_default=text("0"))
    social_security_eligible:bool = Column(Integer, nullable=False, server_default=text("1"))
    user_id:int = Column(ForeignKey('users.user_id'), nullable=False, server_default=text("1"))
    is_partner_income:bool = Column(Integer, nullable=False, server_default=text("0"))


class Kid(Base):
    """Represents each individual child

    Args:
        Base : sqlalchemy declarative_base()

    Attributes: details found in `data/param_details.json`
    """
    __tablename__ = 'kids'
    kid_id:int = Column(Integer, primary_key=True, autoincrement=True)
    user_id:int = Column(ForeignKey('users.user_id'), nullable=False, server_default=text("1"))
    birth_year:int = Column(Integer, nullable=False, server_default=text("2020"))


class User(Base):
    """Main class for representing user data

    Args:
        Base : sqlalchemy declarative_base()

    Attributes: 
        earnings (list[EarningsRecord]): EarningsRecords with matching user_id
        income_profiles (list[JobIncome]): JobIncomes with matching user_id
        kids (list[Kid]): Kids with matching user_id
        other attribute details found in `data/param_details.json`
    """
    __tablename__ = 'users'
    earnings:list[EarningsRecord] = relationship('EarningsRecord', backref='user')
    income_profiles:list[JobIncome] = relationship('JobIncome', backref='user')
    kids:list[Kid] = relationship('Kid', backref='user')

    user_id:int = Column(Integer, primary_key=True, autoincrement=True)
    age:int = SuperColumn(Integer, nullable=False, server_default=text("29"),
                          label_text = 'Your Age', help_text="Current age of user")
    partner:bool = SuperColumn(Integer, nullable=False, server_default=text("1"),
                               label_text='Partner', help_text='Do you have a partner? If \
                                   unchecked, all partner related parameters will be ignored')
    partner_age:int = SuperColumn(Integer, nullable=False, server_default=text("34"),
                                  label_text="Partner's Age", help_text='Current age of partner')
    calculate_til:float = SuperColumn(Float, nullable=False, server_default=text("2090"),
                                      label_text='Simulation End Year', help_text='Final year for \
                                          simulation. Recommended value: birth year + 90')
    current_net_worth:float = SuperColumn(Float, nullable=False, server_default=text("250"),
                                          label_text='Current Net Worth (in $1000s)',
                                          help_text='Current net worth in $1000s')
    yearly_spending:float = SuperColumn(Float, nullable=False, server_default=text("60"),
                                        label_text='Yearly Spending (in $1000s)',
                                        help_text='Total household spending in $1000s')
    state:str = SuperColumn(Text, nullable=False, server_default=text("'California'"),
                            label_text='State of Residence',
                            help_text='State of residence for tax purposes',
                            options = [
                                "California",
                                "New York"
                            ])
    drawdown_tax_rate:float = SuperColumn(Float, nullable=False, server_default=text(".1"),
                                          label_text='Drawdown Tax Rate', help_text='Assumed \
                                              average rate of tax on portfolio drawdown. 15% and \
                                                  20% are the marginal capital gains rates, but \
                                                      the average rate will depend on your mix of \
                                                          tax-advantaged accounts at the point of \
                                                              retirement.')
    cost_of_kid:float = SuperColumn(Float, nullable=False, server_default=text(".12"),
                                    label_text='Cost of Each Child (% Spending)',
                                    help_text='Estimate for average cost of kid as a percentage of \
                                        spending.\n A value of 0.12 increases spending by 12% for \
                                            each child for 22 years after their birth.')
    spending_method:str = SuperColumn(Text, nullable=False, server_default=text("'ceil-floor'"),
                                      label_text='Spending Adjustment Method',
                                      help_text='Controls how spending changes each year.\n\
                                          Inflation-only: increases spending by the inflation rate \
                                              for that year.\n Ceil-floor allows spending to \
                                                  increase when market returns are higher than \
                                                      expected, while lower than expected market \
                                                          returns require decreased spending.',
                                       options = [
                                           "ceil-floor",
                                           "inflation-only"
                                       ],
                                       optimizable = True)
    allowed_fluctuation:float = SuperColumn(Float, server_default=text("0.05"),
                                            label_text='Ceiling-Floor Fluctuation (% of Spending)',
                                            help_text='If using the ceil-floor method of spending, \
                                                spending fluctuates by +/-5% (for value of 0.05) \
                                                    depending on market returns.')
    allocation_method:str = SuperColumn(Text, nullable=False, server_default=text("'Flat'"),
                                        label_text='Portfolio Allocation Method',
                                        help_text='Equity / Bond allocation. \n Life Cycle: uses \
                                            the lifecycle investing method of 100% equities \
                                                allocation until equity target met.\n Flat: Keeps \
                                                    a constant ratio between bonds and equities.\n \
                                                        x minus age: equity allocation decreases \
                                                            with age linearly (120 minus age: at \
                                                                age 40, equity allocation is 80%).\
                                                                    \n Bond tent: increase bonds \
                                                                        till peak year, decrease \
                                                                            bonds afterwards.',
                                        options = [
                                            "Life Cycle",
                                            "Flat",
                                            "120 Minus Age",
                                            "110 Minus Age",
                                            "100 Minus Age",
                                            "Bond Tent"
                                        ],
                                       optimizable = True)
    real_estate_equity_ratio:float = SuperColumn(Float, nullable=False, server_default=text("0.6"),
                                                 label_text='Real Estate Ratio',
                                                 help_text='Ratio of real estate within equity \
                                                     allocation.\n If value set to 0.5, but bonds \
                                                         are 20%, allocation will be 40% real \
                                                             estate, 40% stock, 20% bonds.',
                                                 options = [
                                                     0.0,
                                                     0.1,
                                                     0.2,
                                                     0.3,
                                                     0.4,
                                                     0.5,
                                                     0.6
                                                 ],
                                                 optimizable = True)
    equity_target:float = SuperColumn(Float, nullable=False, server_default=text("1500"),
                                      label_text='Equity Target',
                                      help_text="When using lifecycle allocation or net-worth \
                                          targets for social security, this value acts as a pivot \
                                              point for the portfolio. If set to 1500 and using \
                                                  lifecycle allocation, portfolio will be in 100% \
                                                      equities until net worth hits $1.5M in \
                                                          today's dollars, then any additonal net \
                                                              worth will be invested in bonds. To \
                                                                  learn more, read about lifecycle \
                                                                      investing: https://www.lifecycleinvesting.net/\
                                                                          , but know this method \
                                                                              does not use \
                                                                                  leverage.",
                                      options = range(500,4000,100),
                                      optimizable = True)
    annuities_instead_of_bonds:bool = SuperColumn(Integer, nullable=False, server_default=text("0"),
                                                  label_text='Annuities Instead of Bonds',
                                                  help_text='Money that would be invested into \
                                                      bonds is instead invested in an annuity.',
                                                  options = [1, 0],
                                                  optimizable = True)
    flat_bond_target:float = SuperColumn(Float, server_default=text("0.2"),
                                         label_text='Flat Bond Target',
                                         help_text='When using the Flat allocation method, this \
                                             value determines the ratio of bonds in the portfolio',
                                         options = [
                                            0.2,
                                            0.3,
                                            0.4,
                                            0.5,
                                            0.6
                                         ],
                                         optimizable = True)
    bond_tent_start_allocation:float = SuperColumn(Float, server_default=text("0"),
                                                   label_text='Bond Tent Start Allocation',
                                                   help_text='When using the bond tent allocation \
                                                       method, this value determines the initial \
                                                           allocation of bonds',
                                                   options = [
                                                    0.0,
                                                    0.1,
                                                    0.2,
                                                    0.3,
                                                    0.4
                                                   ],
                                                   optimizable = True)
    bond_tent_start_date:float = SuperColumn(Float, server_default=text("2035"),
                                             label_text='Bond Tent Start Date',
                                             help_text='When using the bond tent allocation \
                                                 method, this value determines the year bond \
                                                     allocation starts to increase')
    bond_tent_peak_allocation:float = SuperColumn(Float, server_default=text("0.8"),
                                                  label_text='Bond Tent Peak Allocation',
                                                  help_text='When using the bond tent allocation \
                                                      method, this value determines the peak \
                                                          allocation of bonds',
                                                  options = [
                                                    0.4,
                                                    0.5,
                                                    0.6,
                                                    0.7,
                                                    0.8
                                                   ],
                                                   optimizable = True)
    bond_tent_peak_date:float = SuperColumn(Float, server_default=text("2040"),
                                            label_text='Bond Tent Peak Date',
                                            help_text='When using the bond tent allocation method, \
                                                this value determines the year bond allocation \
                                                    peaks')
    bond_tent_end_allocation:float = SuperColumn(Float, server_default=text("0.0"),
                                                 label_text='Bond Tent End Allocation',
                                                 help_text='When using the bond tent allocation \
                                                     method, this value determines the final \
                                                         allocation of bonds',
                                                 options = [
                                                    0.0,
                                                    0.1,
                                                    0.2,
                                                    0.3,
                                                    0.4
                                                   ],
                                                 optimizable = True)
    bond_tent_end_date:float = SuperColumn(Float, server_default=text("2060"),
                                           label_text='Bond Tent End Date',
                                           help_text='When using the bond tent allocation method, \
                                               this value determines the year bond allocation gets \
                                                   to final default_value')
    social_security_method:str = SuperColumn(Text, nullable=False, server_default=text("'mid'"),
                                             label_text='Your Social Security Method',
                                             help_text="Models the age at which you take social \
                                                 security.\n Early age = 62, mid age = 66, late \
                                                     age = 70.\n Net worth method triggers social \
                                                         security if you haven't met your equity \
                                                             target or at the late age if you \
                                                                 have.",
                                             options = [
                                                "early",
                                                "mid",
                                                "late",
                                                "net worth"
                                             ],
                                             optimizable = True)
    partner_social_security_method:str = SuperColumn(Text, nullable=False,
                                                     server_default=text("'mid'"),
                                                     label_text="Partner's Social Security Method",
                                                     help_text="Models the date at which your \
                                                         partner takes social security.\n Early \
                                                             age = 62, mid age = 66, late age = \
                                                                 70.\n Net worth method triggers \
                                                                     social security if you \
                                                                         haven't met your equity \
                                                                             target or at the late \
                                                                                 age if you have.",
                                                     options = [
                                                        "early",
                                                        "mid",
                                                        "late",
                                                        "net worth"
                                                     ],
                                                     optimizable = True)
    pension_trust_factor:float = SuperColumn(Float, nullable=False, server_default=text("0.8"),
                                             label_text='Pension Trust Factor',
                                             help_text='Many people are skeptical of relying on \
                                                 social security. A value of 0.8 models your \
                                                     social security payment as 80% of what the \
                                                         current social security administration \
                                                             would provide given your earnings \
                                                                 record.')
    retirement_spending_change:float = SuperColumn(Float, nullable=False,
                                                   server_default=text("-0.15"),
                                                   label_text='Spending Change in Retirement (% of \
                                                       Current Spending)',
                                                   help_text='Many people decrease spending in \
                                                       retirement. A value of -0.15 decreases \
                                                           spending by 15% once neither you nor \
                                                               your partner are earning income.')
    pension:bool = SuperColumn(Integer, nullable=False, server_default=text("0"),
                               label_text='Pension Eligible',
                               help_text='Are you going to receive a pension? If so, social \
                                   security payment is decreased')
    partner_pension:bool = SuperColumn(Integer, nullable=False, server_default=text("0"),
                                       label_text='Partner Pension Eligible',
                                       help_text='Is your partner going to receive a pension? If \
                                           so, social security payment is decreased')
    admin:bool = SuperColumn(Integer, nullable=False, server_default=text("0"),
                             label_text='Admin', help_text='Only applies for admin. Keep 0.')
    admin_pension_method:str = SuperColumn(Text, server_default=text("'early'"),
                                           label_text='Admin Pension Method',
                                           help_text='Only applies for admin',
                                           options = [
                                               "early",
                                               "mid",
                                               "late",
                                               "net worth",
                                               "cash-out"
                                           ],
                                           optimizable = True)

def default_user() -> User:
    """Generate a user with default parameters
    
    User includes attached earnings, income_profiles, and kids generated with
    other default values.

    Returns:
        user.User: User with default values
    """
    earnings = [EarningsRecord(year=2012+i, earnings=30+i*5) for i in range(10)]\
        + [EarningsRecord(is_partner_earnings=1, year=2014+i, earnings=110+i*10) for i in range(4)]
    income_profiles = [JobIncome(), JobIncome(starting_income=70, tax_deferred_income=18,
                                              last_date=2040, try_to_optimize=1,
                                              social_security_eligible=0, is_partner_income=1)]
    kids = [Kid(), Kid(birth_year=2025)]
    return User(earnings=earnings, income_profiles=income_profiles, kids=kids)
