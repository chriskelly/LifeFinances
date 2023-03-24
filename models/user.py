"""Module for representing User object and SQL table structure

This module defines the attributes of a user and the default values populated into the database.

"""
from decimal import Decimal, getcontext
from sqlalchemy import Column, Float, ForeignKey, Integer, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
# From ChatGPT: Defining a property with the same name as a column in your SQLAlchemy model
# can lead to unexpected behavior, so it's generally not recommended.
# However, if you still want to define a property with the same name that
# automatically converts the string value to a Decimal object, you can use a hybrid property.
# A hybrid property is a special type of property that can be accessed as either
# an instance attribute or a class attribute, depending on how it's called.

getcontext().prec = 2 # set Decimal precision
Base = declarative_base()

class EarningsRecord(Base):
    __tablename__ = 'earnings_records'
    earnings_id:int = Column(Integer, primary_key=True, autoincrement=True)
    user_id:int = Column(ForeignKey('users.user_id'), nullable=False, server_default=text("1"))
    is_partner_earnings:bool = Column(Integer, nullable=False, server_default=text("0"))
    year:int = Column(Integer, nullable=False, server_default=text("0"))
    earnings:float = Column(Float, nullable=False, server_default=text("0"))


class JobIncome(Base):
    __tablename__ = 'job_incomes'
    job_income_id:int = Column(Integer, primary_key=True, autoincrement=True)
    starting_income:float = Column(Float, nullable=False, server_default=text("50"))
    tax_deferred_income:float = Column(Float, nullable=False, server_default=text("10"))
    _last_date = Column(Text, nullable=False, server_default=text("2035.25"))
    @hybrid_property
    def last_date(self):
        return Decimal(self._last_date)
    @last_date.setter
    def last_date(self, value):
        self._last_date = str(value)
    yearly_raise:float = Column(Float, nullable=False, server_default=text("0.04"))
    try_to_optimize:bool = Column(Integer, nullable=False, server_default=text("0"))
    social_security_eligible:bool = Column(Integer, nullable=False, server_default=text("1"))
    user_id:int = Column(ForeignKey('users.user_id'), nullable=False, server_default=text("1"))
    is_partner_income:bool = Column(Integer, nullable=False, server_default=text("0"))


class Kid(Base):
    __tablename__ = 'kids'
    kid_id:int = Column(Integer, primary_key=True, autoincrement=True)
    user_id:int = Column(ForeignKey('users.user_id'), nullable=False, server_default=text("1"))
    birth_year:int = Column(Integer, nullable=False, server_default=text("2020"))


class User(Base):
    __tablename__ = 'users'
    earnings:list[EarningsRecord] = relationship('EarningsRecord', backref='user')
    income_profiles:list[JobIncome] = relationship('JobIncome', backref='user')
    kids:list[Kid] = relationship('Kid', backref='user')
    
    user_id:int = Column(Integer, primary_key=True, autoincrement=True)
    user_age:int = Column(Integer, nullable=False, server_default=text("29"))
    partner:bool = Column(Integer, nullable=False, server_default=text("1"))
    partner_age:int = Column(Integer, nullable=False, server_default=text("34"))
    _calculate_til = Column(Text, nullable=False, server_default=text("2090"))
    @hybrid_property
    def calculate_til(self):
        return Decimal(self._calculate_til)
    @calculate_til.setter
    def calculate_til(self, value):
        self._calculate_til = str(value)
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
    _bond_tent_start_date = Column(Text, server_default=text("2035"))
    @hybrid_property
    def bond_tent_start_date(self):
        return Decimal(self._bond_tent_start_date)
    @bond_tent_start_date.setter
    def bond_tent_start_date(self, value):
        self._bond_tent_start_date = str(value)
    bond_tent_peak_allocation:float = Column(Float, server_default=text("0.8"))
    _bond_tent_peak_date = Column(Text, server_default=text("2040"))
    @hybrid_property
    def bond_tent_peak_date(self):
        return Decimal(self._bond_tent_peak_date)
    @bond_tent_peak_date.setter
    def bond_tent_peak_date(self, value):
        self._bond_tent_peak_date = str(value)
    bond_tent_end_allocation:float = Column(Float, server_default=text("0.0"))
    _bond_tent_end_date = Column(Text, server_default=text("2060"))
    @hybrid_property
    def bond_tent_end_date(self):
        return Decimal(self._bond_tent_end_date)
    @bond_tent_end_date.setter
    def bond_tent_end_date(self, value):
        self._bond_tent_end_date = str(value)
    user_social_security_method:str = Column(Text, nullable=False, server_default=text("'mid'"))
    partner_social_security_method:str = Column(Text, nullable=False, server_default=text("'mid'"))
    pension_trust_factor:float = Column(Float, nullable=False, server_default=text("0.8"))
    retirement_spending_change:float = Column(Float, nullable=False, server_default=text("-0.15"))
    user_pension:bool = Column(Integer, nullable=False, server_default=text("0"))
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
                                              _last_date=2040, try_to_optimize=1,
                                              social_security_eligible=0, is_partner_income=1)]
    kids = [Kid(), Kid(birth_year=2025)]
    return User(earnings=earnings, income_profiles=income_profiles, kids=kids)
