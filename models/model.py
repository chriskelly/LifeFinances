"""Module for handling parameters for user

This module has functions for handling parameters and loading/savings
from the SQLite database

Required installations are detailed in requirements.txt.

This file contains the following functions:

    * load_params() - Pulls parameter values from the database
    * copy_default_values() - Overwrite the user database with the default database
    * db_cmd() - Send a query to the database
    * Model.log_to_optimize_page() - Use a web socket connection to log to the optimizer page
    * Model.save_from_genetic() - Save parameters changed by genetic.main()
    * Model.save_from_flask - Save paramters changed on the parameter.html page
    * Model.add_to_special_tables() - Save new instances of unique data types
    * Model.remove_from_special_tables() - Delete instance from unique data type table
"""

# import shutil
import json
import datetime as dt
import sqlalchemy as db
import sqlalchemy.orm as orm
from flask_socketio import SocketIO
import data.constants as const
from models.user import Base, User, default_user

# def copy_default_values():
#     """Overwrite the user database with the default database"""
#     shutil.copy(const.DEFAULT_DB_LOC, const.DB_LOC)

# Generate the database schema
engine = db.create_engine(f'sqlite:///{const.DB_LOC}')
USER_ID = 1 # Default User ID is 1 until we support user login
with orm.Session(engine) as session:
    try: # check for database not in data folder yet
        with open(const.DB_LOC, encoding="utf-8"):
            pass
    except FileNotFoundError:
        session.add(default_user())
    Base.metadata.create_all(engine)
    # Attributes need to be eager/joined loaded to ensure they are accessable
    # after the session is closed. https://docs.sqlalchemy.org/en/14/errors.html#error-bhk3
    session.expire_on_commit = False
    user = session.query(User).options(orm.joinedload(User.earnings),
                                       orm.joinedload(User.income_profiles),
                                       orm.joinedload(User.kids)).filter_by(user_id=USER_ID).one()
    session.commit() # commit() is optional unless data is added to database

TODAY = dt.date.today()
TODAY_QUARTER = (TODAY.month-1)//3
TODAY_YR = TODAY.year
TODAY_YR_QT = TODAY.year+TODAY_QUARTER*.25
# engine = db.create_engine(f'sqlite:///{const.DB_LOC}')

class Model:
    """An instance of Model is used to keep track of a collection of parameters

    Attributes
    ----------
    param_vals : dict
        {Parameter:value} that contribute to financial calculations
    param_details : dict
        {Parameter:detail obj} that shows details for a parameter such as type and range of options
    """
    def __init__(self, socketio:SocketIO = None):
        self.param_vals, self.param_details = load_params()
        self.socketio = socketio

    def log_to_optimize_page(self, log:str):
        """Emit a log message to the optimize page using SocketIO

        Args:
            log (str): Message for logging
        """
        if self.socketio:
            self.socketio.emit('new_log', {'log': log}, namespace='/optimize')

    def save_from_genetic(self, mute_param_vals:dict, reduce_dates:bool):
        """Save the mutable paramater values into the database.
        If reduce_dates: reduce all the job last_dates by
        one quarter if they're marked try_to_optimize

        Args:
            mute_param_vals (dict): {param:value} for mutable params,
                assumes they're only in the 'users' Table of the database
            reduce_dates (bool): whether or not to reduce the last_dates in the database

        Raises:
            Exception: if reducing the job last_date would make the job never start.
        """
        for param,val in mute_param_vals.items():
            cmd = f'UPDATE users SET {param} = ? WHERE user_id = ?'
            # Can't use SQL objects as placeholders https://stackoverflow.com/a/25387570/13627745
            db_cmd(cmd,(val,USER_ID))
        if reduce_dates:
            # Reduce all last dates by one quarter
                # Assuming dates for bond tent also needs to be reduced with earlier retire date
            for param in ['bond_tent_start_date','bond_tent_peak_date','bond_tent_end_date']:
                cmd = f'UPDATE users SET {param} = ? WHERE user_id = ?'
                db_cmd(cmd,(self.param_vals[param]-0.25, USER_ID))
                # Reduce income stop dates
            for usr in ['user','partner']:
                start_date = TODAY_YR_QT
                for job in self.param_vals[f'{usr}_jobs']:
                    last_date = job['last_date']
                    duration = last_date - start_date + 0.25
                    reduce = bool(job['try_to_optimize'])
                    # check if job will start before previous job ends
                    if duration <= 0.25 and reduce:
                        raise ValueError(f'Income with Last Date of\
                            {job["last_date"]} ends too early')
                        # Not sure how to better handle this. You could delete the income item
                        # in the params, but I don't think users would prefer the income be deleted.
                        # You could add some sort of skip tag to the income that income.py
                        # then uses to ignore, but that may not be easily debuggable
                    if reduce:
                        cmd = 'UPDATE job_incomes SET last_date = ?\
                            WHERE user_id = ? AND job_income_id = ?'
                        db_cmd(cmd,(job['last_date']-0.25, USER_ID, job['job_income_id']))
                        print(f"Now trying to reduce {usr}'s last date to {last_date-0.25}!")
                        self.log_to_optimize_page(f"Now trying to reduce {usr}'s\
                            last date to {last_date-0.25}!")
                    start_date = last_date + 0.25 # adjust start_date for next income
        self.param_vals, _ = load_params()

    def save_from_flask(self, form: dict[str,str]):
        """Save the form results into the database.

        Args:
            form (dict[str,str]): (param:str(value))
        """
        form_set = set()
        for key, val in form.items():
            if key in ['save', 'remove_row', 'add_row']:
                continue
            if key in form_set:
                continue # avoid duplicates from checkboxes. Only the first should be counted
            else: form_set.add(key)
            if val.isdigit():
                val = int(val)
            elif _is_float(val):
                val = float(val)
            elif val == "True":
                val = 1
            elif val == "False":
                val = 0

            # if the key matches the db name exactly, it isn't a special key
            if key in self.param_vals:
                # Can't use SQL objects as placeholders
                # https://stackoverflow.com/a/25387570/13627745
                cmd = f'UPDATE users SET {key} = ? WHERE user_id = ?'
                db_cmd(cmd,(val,USER_ID))
                continue
            else:
                try:
                    key, idx, sub_k = key.split('@')
                except ValueError:
                    key, idx = key.split('@')
            # job incomes
            if key in ['user_jobs','partner_jobs']:
                cmd = f'UPDATE job_incomes SET {sub_k} = ? WHERE user_id = ? AND job_income_id = ?'
            # kid birth years
            elif key == 'kid_birth_years':
                cmd = 'UPDATE kids SET birth_year = ? WHERE user_id = ? AND kid_id = ?'
            # earnings record
            elif key in ['user_earnings_record','partner_earnings_record']:
                cmd = f'UPDATE earnings_records SET {sub_k}\
                    = ? WHERE user_id = ? AND earnings_id = ?'
            db_cmd(cmd,(val,USER_ID,idx))
        self.param_vals, _ = load_params()

    def add_to_special_tables(self,param:str):
        """Inserts one row into the table related to the passed in param and reloads the param_vals

        Args:
            param (str): parameter to determine table and partner status
        """
        if param == 'user_jobs':
            db_cmd(db.text('INSERT INTO job_incomes DEFAULT VALUES'))
        elif param == 'partner_jobs':
            db_cmd(db.text('INSERT INTO job_incomes (is_partner_income) VALUES (1)'))
        elif param == 'kid_birth_years':
            db_cmd(db.text('INSERT INTO kids DEFAULT VALUES'))
        elif param == 'user_earnings_record':
            db_cmd(db.text('INSERT INTO earnings_records DEFAULT VALUES'))
        elif param == 'partner_earnings_record':
            db_cmd(db.text('INSERT INTO earnings_records (is_partner_earnings) VALUES (1)'))
        self.param_vals, _ = load_params()

    def remove_from_special_tables(self,table_id:str):
        """Remove a row from a specific table and reloads the param_vals

        Args:
            table_id (str): 'table@id': str that combines the table being accessed
                                        and the id of the row in the table
        """
        table, idx = table_id.split('@')
        if table == 'job_incomes':
            cmd = db.text(f'DELETE FROM job_incomes WHERE job_income_id = {idx}')
        elif table == 'kids':
            cmd = db.text(f'DELETE FROM kids WHERE kid_id = {idx}')
        elif table == 'earnings_records':
            cmd = db.text(f'DELETE FROM earnings_records WHERE earnings_id = {idx}')
        # db_cmd(cmd,(idx,)) # can't get to work.
            # Keeps giving error for not enough binding arguements
        db_cmd(cmd)
        self.param_vals, _ = load_params()

def load_params():
    """Pulls parameter values from data/data.db and parameter details from data/param_detail.json

    Returns:
        dict: param_vals = {param:val} \n
        dict: param_details = {param:detail object}
    """
    res, headers = db_cmd(db.text(f'SELECT * FROM users WHERE user_id == {USER_ID}'))
    param_vals = {param:value for param, value in zip(headers,res[0])}
    del param_vals['user_id'] # not needed and doesn't have a match in param_details
        # historic earnings for social security
    usr_earnings, _ = db_cmd(db.text(f'SELECT * from earnings_records WHERE\
                            user_id == {USER_ID} AND is_partner_earnings == 0'))
    partner_earnings, _ = db_cmd(db.text(f'SELECT * from earnings_records WHERE\
                            user_id == {USER_ID} AND is_partner_earnings == 1'))
    param_vals['user_earnings_record'] = [[idx,year,earnings] for
                                          idx,_,_,year,earnings in usr_earnings]
    param_vals['partner_earnings_record'] = [[idx,year,earnings] for
                                             idx,_,_,year,earnings in partner_earnings]
        # kid birth years
    birth_years, _ = db_cmd(db.text(f'SELECT * from kids WHERE user_id == {USER_ID}'))
    param_vals['kid_birth_years'] = [[idx,year] for idx,_,year in birth_years]
        # income from jobs
    usr_job_incomes, descriptions = db_cmd(db.text(f'SELECT * from job_incomes\
                                    WHERE user_id == {USER_ID} AND is_partner_income == 0'))
    partner_job_incomes, _ = db_cmd(db.text(f'SELECT * from job_incomes\
                                    WHERE user_id == {USER_ID} AND is_partner_income == 1'))
        # Use dict comprehension (to get sub-parameters) in a list comprehension (to get all jobs)
    param_vals['user_jobs'] = [{key:val for key,val in zip(descriptions,job) if key not in\
                                {'user_id','is_partner_income'}} for job in usr_job_incomes]
    param_vals['partner_jobs'] = [{key:val for key,val in zip(descriptions,job) if key not in\
                                {'user_id','is_partner_income'}} for job in partner_job_incomes]
    # get param details
    with open(const.PARAM_DETAILS_LOC, encoding="utf-8") as json_file:
        param_details:dict = json.load(json_file)
    return param_vals, param_details

def db_cmd(cmd,cmd_args:tuple=None) -> tuple[list, list]:
    """Provide the query result to the provided command string

    Args:
        sql_cmd (_Executable): SQLAlchemy statement that can be executed
        cmd_args (tuple): Any arguements that need to be passed into the sql_cmd

    Returns:
        list: all output rows from query \n
        list: column names
    """
    with engine.connect() as conn:
        if cmd_args: # Used to avoid SQL injection attacks
            res = conn.execute(cmd,cmd_args)
        else:
            res = conn.execute(cmd)
        try:
            return res.fetchall(), res.keys()
        except db.exc.ResourceClosedError: # some commands won't have a return
            pass

def _is_float(element):
    """Checks whether the element can be converted to a float

    Parameters
    ----------
    element : any

    Returns
    -------
    bool

    """
    try:
        float(element)
        return True
    except ValueError:
        return False
