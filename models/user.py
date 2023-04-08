"""Module for representing User object and SQL table structure

This module defines the attributes of a user and the default values populated into the database.

"""
from sqlalchemy import Column, Float, ForeignKey, Integer, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
# From ChatGPT: Defining a property with the same name as a column in your SQLAlchemy model
# can lead to unexpected behavior, so it's generally not recommended.
# However, if you still want to define a property with the same name that
# automatically converts the string value to a Decimal object, you can use a hybrid property.
# A hybrid property is a special type of property that can be accessed as either
# an instance attribute or a class attribute, depending on how it's called.

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
    age:int = Column(Integer, nullable=False, server_default=text("29"))
    partner:bool = Column(Integer, nullable=False, server_default=text("1"))
    partner_age:int = Column(Integer, nullable=False, server_default=text("34"))
    calculate_til:float = Column(Float, nullable=False, server_default=text("2090"))
    current_net_worth:float = Column(Float, nullable=False, server_default=text("250"))
    yearly_spending:float = Column(Float, nullable=False, server_default=text("60"))
    state:str = Column(Text, nullable=False, server_default=text("'California'"))
    drawdown_tax_rate:float = Column(Float, nullable=False, server_default=text(".1"))
    cost_of_kid:float = Column(Float, nullable=False, server_default=text(".12"))
    spending_method:str = Column(Text, nullable=False, server_default=text("'ceil-floor'"))
    allowed_fluctuation:float = Column(Float, server_default=text("0.05"))
    allocation_method:str = Column(Text, nullable=False, server_default=text("'Flat'"))
    real_estate_equity_ratio:float = Column(Float, nullable=False, server_default=text("0.6"))
    equity_target:float = Column(Float, nullable=False, server_default=text("1500"))
    annuities_instead_of_bonds = Column(Integer, nullable=False, server_default=text("0"))
    flat_bond_target:float = Column(Float, server_default=text("0.2"))
    bond_tent_start_allocation:float = Column(Float, server_default=text("0"))
    bond_tent_start_date:float = Column(Float, server_default=text("2035"))
    bond_tent_peak_allocation:float = Column(Float, server_default=text("0.8"))
    bond_tent_peak_date:float = Column(Float, server_default=text("2040"))
    bond_tent_end_allocation:float = Column(Float, server_default=text("0.0"))
    bond_tent_end_date:float = Column(Float, server_default=text("2060"))
    social_security_method:str = Column(Text, nullable=False, server_default=text("'mid'"))
    partner_social_security_method:str = Column(Text, nullable=False, server_default=text("'mid'"))
    pension_trust_factor:float = Column(Float, nullable=False, server_default=text("0.8"))
    retirement_spending_change:float = Column(Float, nullable=False, server_default=text("-0.15"))
    pension:bool = Column(Integer, nullable=False, server_default=text("0"))
    partner_pension:bool = Column(Integer, nullable=False, server_default=text("0"))
    admin:bool = Column(Integer, nullable=False, server_default=text("0"))
    admin_pension_method:str = Column(Text, server_default=text("'early'"))

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
