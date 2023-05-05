"""Module for representing User object and SQL table structure

This module defines the attributes of a user and the default values populated into the database.

"""
from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm, ModelFieldList
from wtforms.fields import FormField, SelectField, SubmitField, HiddenField
from app import db

class SuperColumn(db.Column):
    """Stores additional information in the Column objects defined for each table"""
    def __init__(self, *args, help_text:str, **kwargs):
        """Stores additional information in the Column objects defined for each table

        Args:
            help_text (str): Text description of item
        
        Kwargs:
            options (iterable): Limited options for Column
            optimizable (bool): Indicates attribute can be modified by the optimizer script
        """
        self.help_text = help_text
        self.options:list = kwargs.pop('options', [])
        self.optimizable:bool = kwargs.pop('optimizable', False)
        super().__init__(*args, **kwargs)

class EarningsRecord(db.Model):
    """A record of income earnings for a specific year

    Earnings are expected to be from the Social Security Administration, and these
    will be used to calculate social security payments.

    Args:
        Base : sqlalchemy declarative_base()
    """
    __tablename__ = 'earnings_records'
    id:int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id:int = db.Column(db.Integer, db.ForeignKey('users.id'))
    year:int = db.Column(db.Integer, nullable=False, server_default=db.text("0"), info={'label':'Year'})
    earnings:float = db.Column(db.Float, nullable=False, server_default=db.text("0"), info={'label':'Earnings'})
    is_partner_earnings:bool = db.Column(db.Boolean, server_default=db.text("0"), info={'label':"Partner's?"})

class JobIncome(db.Model):
    """Represents total income earned by individual during specific period of time

    Args:
        Base : sqlalchemy declarative_base()
    """
    __tablename__ = 'job_incomes'
    id:int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    last_date:float = db.Column(db.Float, nullable=False, server_default=db.text("2035.25"), info={'label':'Last Date'})
    starting_income:float = db.Column(db.Float, nullable=False, server_default=db.text("50"), info={'label':'Salary'})
    tax_deferred_income:float = db.Column(db.Float, nullable=False, server_default=db.text("10"), info={'label':'Tax Deferred Income'})
    yearly_raise:float = db.Column(db.Float, nullable=False, server_default=db.text("0.04"), info={'label':'Yearly Increase'})
    try_to_optimize:bool = db.Column(db.Boolean, server_default=db.text("0"), info={'label':'Try to Optimize?'})
    social_security_eligible:bool = db.Column(db.Boolean,
                                              server_default=db.text("1"), info={'label':'Social Security Eligible?'})
    user_id:int = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_partner_income:bool = db.Column(db.Boolean, server_default=db.text("0"), info={'label':"Partner's?"})

class Kid(db.Model):
    """Represents each individual child

    Args:
        Base : sqlalchemy declarative_base()
    """
    __tablename__ = 'kids'
    id:int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id:int = db.Column(db.Integer, db.ForeignKey('users.id'))
    birth_year:int = db.Column(db.Integer, nullable=False, server_default=db.text("2020"), info={'label':'Birth Year'})

class User(db.Model):
    """Main class for representing user data

    Args:
        Base : sqlalchemy declarative_base()

    Attributes: 
        earnings (list[EarningsRecord]): EarningsRecords with matching user_id
        income_profiles (list[JobIncome]): JobIncomes with matching user_id
        kids (list[Kid]): Kids with matching user_id
        other attribute details found in help_text attributes
    """
    __tablename__ = 'users'

    def optimizable_parameters(self) -> list[str]:
        """All parameters that are set to optimizable
        
        The return will be different if there's code that modifies the User class
        to change the boolean state of 'optimizable' in the Superdb.Column attributes.

        Returns:
            list[str]: List of User optimizable attributes (in string form)
        """
        return [key for key, _ in self.__dict__.items()
                if key in User.__dict__
                and 'optimizable' in User.__dict__[key].expression.__dict__
                and User.__dict__[key].expression.__dict__['optimizable']]

    earnings:list[EarningsRecord] = db.relationship('EarningsRecord', backref='user')
    income_profiles:list[JobIncome] = db.relationship('JobIncome', backref='user')
    kids:list[Kid] = db.relationship('Kid', backref='user')

    id:int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    age:int = SuperColumn(db.Integer, nullable=False, server_default=db.text("29"),
                          info={'label': 'Your Age'}, help_text="Current age of user")
    partner:bool = SuperColumn(db.Boolean, server_default=db.text("1"),
                               info={'label':'Partner'}, help_text='Do you have a partner? If \
                                   unchecked, all partner related parameters will be ignored')
    partner_age:int = SuperColumn(db.Integer, nullable=False, server_default=db.text("34"),
                                  info={'label':"Partner's Age"}, help_text='Current age of partner')
    calculate_til:float = SuperColumn(db.Float, nullable=False, server_default=db.text("2090"),
                                      info={'label':'Simulation End Year'}, help_text='Final year for \
                                          simulation. Recommended value: birth year + 90')
    current_net_worth:float = SuperColumn(db.Float, nullable=False, server_default=db.text("250"),
                                          info={'label':'Current Net Worth (in $1000s)'},
                                          help_text='Current net worth in $1000s')
    yearly_spending:float = SuperColumn(db.Float, nullable=False, server_default=db.text("60"),
                                        info={'label':'Yearly Spending (in $1000s)'},
                                        help_text='Total household spending in $1000s')
    state:str = SuperColumn(db.Text, nullable=False, server_default=db.text("'California'"),
                            info={'label':'State of Residence'},
                            help_text='State of residence for tax purposes',
                            options = [
                                "California",
                                "New York"
                            ])
    drawdown_tax_rate:float = SuperColumn(db.Float, nullable=False, server_default=db.text(".1"),
                                          info={'label':'Drawdown Tax Rate'}, help_text='Assumed \
                                              average rate of tax on portfolio drawdown. 15% and \
                                                  20% are the marginal capital gains rates, but \
                                                      the average rate will depend on your mix of \
                                                          tax-advantaged accounts at the point of \
                                                              retirement.')
    cost_of_kid:float = SuperColumn(db.Float, nullable=False, server_default=db.text(".12"),
                                    info={'label':'Cost of Each Child (% Spending)'},
                                    help_text='Estimate for average cost of kid as a percentage of \
                                        spending.\n A value of 0.12 increases spending by 12% for \
                                            each child for 22 years after their birth.')
    spending_method:str = SuperColumn(db.Text, nullable=False,
                                      server_default=db.text("'ceil-floor'"),
                                      info={'label':'Spending Adjustment Method'},
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
    allowed_fluctuation:float = SuperColumn(db.Float, server_default=db.text("0.05"),
                                            info={'label':'Ceiling-Floor Fluctuation (% of Spending)'},
                                            help_text='If using the ceil-floor method of spending, \
                                                spending fluctuates by +/-5% (for value of 0.05) \
                                                    depending on market returns.')
    allocation_method:str = SuperColumn(db.Text, nullable=False, server_default=db.text("'Flat'"),
                                        info={'label':'Portfolio Allocation Method'},
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
    real_estate_equity_ratio:float = SuperColumn(db.Float, nullable=False,
                                                 server_default=db.text("0.6"),
                                                 info={'label':'Real Estate Ratio'},
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
    equity_target:float = SuperColumn(db.Float, nullable=False, server_default=db.text("1500"),
                                      info={'label':'Equity Target'},
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
                                      options = list(range(500,4000,100)),
                                      optimizable = True)
    annuities_instead_of_bonds:bool = SuperColumn(db.Boolean,                                                  server_default=db.text("0"),
                                                  info={'label':'Annuities Instead of Bonds'},
                                                  help_text='Money that would be invested into \
                                                      bonds is instead invested in an annuity.',
                                                  options = [1, 0],
                                                  optimizable = True)
    flat_bond_target:float = SuperColumn(db.Float, server_default=db.text("0.2"),
                                         info={'label':'Flat Bond Target'},
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
    bond_tent_start_allocation:float = SuperColumn(db.Float, server_default=db.text("0"),
                                                   info={'label':'Bond Tent Start Allocation'},
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
    bond_tent_start_date:float = SuperColumn(db.Float, server_default=db.text("2035"),
                                             info={'label':'Bond Tent Start Date'},
                                             help_text='When using the bond tent allocation \
                                                 method, this value determines the year bond \
                                                     allocation starts to increase')
    bond_tent_peak_allocation:float = SuperColumn(db.Float, server_default=db.text("0.8"),
                                                  info={'label':'Bond Tent Peak Allocation'},
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
    bond_tent_peak_date:float = SuperColumn(db.Float, server_default=db.text("2040"),
                                            info={'label':'Bond Tent Peak Date'},
                                            help_text='When using the bond tent allocation method, \
                                                this value determines the year bond allocation \
                                                    peaks')
    bond_tent_end_allocation:float = SuperColumn(db.Float, server_default=db.text("0.0"),
                                                 info={'label':'Bond Tent End Allocation'},
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
    bond_tent_end_date:float = SuperColumn(db.Float, server_default=db.text("2060"),
                                           info={'label':'Bond Tent End Date'},
                                           help_text='When using the bond tent allocation method, \
                                               this value determines the year bond allocation gets \
                                                   to final default_value')
    social_security_method:str = SuperColumn(db.Text, nullable=False,
                                             server_default=db.text("'mid'"),
                                             info={'label':'Your Social Security Method'},
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
    partner_social_security_method:str = SuperColumn(db.Text, nullable=False,
                                                     server_default=db.text("'mid'"),
                                                     info={'label':"Partner's Social Security Method"},
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
    pension_trust_factor:float = SuperColumn(db.Float, nullable=False,
                                             server_default=db.text("0.8"),
                                             info={'label':'Pension Trust Factor'},
                                             help_text='Many people are skeptical of relying on \
                                                 social security. A value of 0.8 models your \
                                                     social security payment as 80% of what the \
                                                         current social security administration \
                                                             would provide given your earnings \
                                                                 record.')
    retirement_spending_change:float = SuperColumn(db.Float, nullable=False,
                                                   server_default=db.text("-0.15"),
                                                   info={'label':'Spending Change in Retirement (% of \
                                                       Current Spending)'},
                                                   help_text='Many people decrease spending in \
                                                       retirement. A value of -0.15 decreases \
                                                           spending by 15% once neither you nor \
                                                               your partner are earning income.')
    pension:bool = SuperColumn(db.Boolean,server_default=db.text("0"),
                               info={'label':'Pension Eligible'},
                               help_text='Are you going to receive a pension? If so, social \
                                   security payment is decreased')
    partner_pension:bool = SuperColumn(db.Boolean,server_default=db.text("0"),
                                       info={'label':'Partner Pension Eligible'},
                                       help_text='Is your partner going to receive a pension? If \
                                           so, social security payment is decreased')
    admin:bool = SuperColumn(db.Boolean,server_default=db.text("0"),
                             info={'label':'Admin'}, help_text='Only applies for admin. Keep 0.')
    admin_pension_method:str = SuperColumn(db.Text, server_default=db.text("'early'"),
                                           info={'label':'Admin Pension Method'},
                                           help_text='Only applies for admin',
                                           options = [
                                               "early",
                                               "mid",
                                               "late",
                                               "net worth",
                                               "cash-out"
                                           ],
                                           optimizable = True)

class EarningsRecordForm(FlaskForm, ModelForm):
    """Form for EarningsRecord class"""
    class Meta:
        """WTForms-Alchemy required class"""
        model = EarningsRecord
    id = HiddenField() # Ensures id stays linked to User object for saving

class JobIncomeForm(FlaskForm, ModelForm):
    """Form for JobIncome class"""
    class Meta:
        """WTForms-Alchemy required class"""
        model = JobIncome
    id = HiddenField()

class KidForm(FlaskForm, ModelForm):
    """Form for Kid class"""
    class Meta:
        """WTForms-Alchemy required class"""
        model = Kid
    id = HiddenField()

class UserForm(FlaskForm, ModelForm):
    """Form for User class"""
    class Meta:
        """WTForms-Alchemy required class"""
        model = User
        exclude = ['admin_pension_method','admin']
    submit = SubmitField('Save')
    earnings = ModelFieldList(FormField(EarningsRecordForm, 'Earning'))
    kids = ModelFieldList(FormField(KidForm, 'Kid'))
    income_profiles = ModelFieldList(FormField(JobIncomeForm, 'Income Profile'))
    state = SelectField(choices=User.state.options)
    spending_method = SelectField(choices=User.spending_method.options)
    allocation_method = SelectField(choices=User.allocation_method.options)
    real_estate_equity_ratio = SelectField(choices=User.real_estate_equity_ratio.options)
    equity_target = SelectField(choices=User.equity_target.options)
    flat_bond_target = SelectField(choices=User.flat_bond_target.options)
    bond_tent_start_allocation = SelectField(choices=User.bond_tent_start_allocation.options)
    bond_tent_peak_allocation = SelectField(choices=User.bond_tent_peak_allocation.options)
    bond_tent_end_allocation = SelectField(choices=User.bond_tent_end_allocation.options)
    social_security_method = SelectField(choices=User.social_security_method.options)
    partner_social_security_method = SelectField(choices
                                                 =User.partner_social_security_method.options)

def append_field(form:UserForm, field):
    if field == 'income':
        form.income_profiles.append_entry(FormField(JobIncomeForm()))
    elif field == 'kid':
        form.kids.append_entry(FormField(KidForm()))
    elif field == 'earning':
        form.earnings.append_entry(FormField(EarningsRecordForm()))

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
