"""Module for handling parameters for user

This module has functions for handling parameters and loading/savings
from the SQLite database

Required installations are detailed in requirements.txt.

This file contains the following functions:

    * initialize_db() - Create database with default user
    * copy_default_values() - Overwrite the user database with the default database
    * db_cmd() - Send a query to the database
    * Model.log_to_optimize_page() - Use a web socket connection to log to the optimizer page
    * Model.save_from_genetic() - Save parameters changed by genetic.main()
    * Model.save_from_flask - Save paramters changed on the parameter.html page
    * Model.add_to_special_tables() - Save new instances of unique data types
    * Model.remove_from_special_tables() - Delete instance from unique data type table
"""
import json
import datetime as dt
from flask_socketio import SocketIO
from app import db, app
import data.constants as const
from models.user import User, default_user

USER_ID = 1 # Default User ID is 1 until we support user login

def initialize_db():
    """Create database with default user"""
    with app.app_context():
        db.create_all()
        db.session.add(default_user())
        db.session.commit()

try: # check for database not in data folder yet
    with open(const.DB_LOC, encoding="utf-8"):
        pass
except FileNotFoundError:
    initialize_db()

TODAY = dt.date.today()
TODAY_QUARTER = (TODAY.month-1)//3
TODAY_YR = TODAY.year
TODAY_YR_QT = TODAY.year+TODAY_QUARTER*.25

class Model:
    """An instance of Model is used to keep track of a collection of parameters

    Attributes
        user (models.user.User): user data 
        
        socketio (SocketIO)
    """
    def __init__(self, socketio:SocketIO = None):
        with app.app_context():
            self.user:User = get_user()
        self.socketio = socketio

    def log_to_optimize_page(self, log:str):
        """Emit a log message to the optimize page using SocketIO

        Args:
            log (str): Message for logging
        """
        if self.socketio:
            self.socketio.emit('new_log', {'log': log}, namespace='/optimize')

    def save_user(self):
        """Update the user in the database.

        Args:
            user (models.user.User): User object with updated parameters
        """
        db.session.add(self.user)
        db.session.commit()

def get_user():
    # Attributes need to be eager/joined loaded to ensure they are accessable
    # after the session is closed. https://docs.sqlalchemy.org/en/14/errors.html#error-bhk3
    return db.session.query(User).filter_by(id=USER_ID).options(
                                        db.joinedload(User.earnings),
                                        db.joinedload(User.income_profiles),
                                        db.joinedload(User.kids)).one()
