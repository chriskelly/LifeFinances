import shutil, json, datetime as dt
import data.constants as const
import sqlalchemy as db

try: # check for database not in data folder yet
    with open(const.DB_LOC): pass 
except FileNotFoundError:
    shutil.copy(const.DEFAULT_DB_LOC, const.DB_LOC) 

TODAY = dt.date.today()
TODAY_QUARTER = (TODAY.month-1)//3
TODAY_YR = TODAY.year
TODAY_YR_QT = TODAY.year+TODAY_QUARTER*.25
USER_ID = 1 # Default User ID is 1 until we support user login
ENGINE = db.create_engine(f'sqlite:///{const.DB_LOC}')

class Model:
    """An instance of Model is used to keep track of a collection of parameters
    
    Attributes
    ----------
    param_vals : dict
        {Named parameter:value} that contribute to financial calculations
    param_details : dict
        {Named parameter:detail obj} that shows details for a parameter such as type and range of options 
    
    """
    def __init__(self):
        self.param_vals, self.param_details = load_params()
        
    def save_from_genetic(self, mute_param_vals:dict, reduce_dates:bool):
        """Save the mutable paramater values into the database.
        If reduce_dates: reduce all the job last_dates by one quarter if they're marked try_to_optimize

        Args:
            mute_param_vals (dict): {param:value} for mutable params, assumes they're only in the 'users' Table of the database
            reduce_dates (bool): whether or not to reduce the last_dates in the database

        Raises:
            Exception: if reducing the job last_date would make the job never start.
        """
        for param,val in mute_param_vals.items():
            cmd = f'UPDATE users SET {param} = ? WHERE user_id = ?' # Can't use SQL objects as placeholders https://stackoverflow.com/a/25387570/13627745
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
                    if duration <= 0.25 and reduce: # check if job will start before previous job ends
                        raise Exception(f'Income with Last Date of {job["last_date"]} ends too early') # Not sure how to better handle this. You could delete the income item in the params, but I don't think users would prefer the income be deleted. You could add some sort of skip tag to the income that income.py then uses to ignore, but that may not be easily debuggable
                    if reduce:
                        cmd = f'UPDATE job_incomes SET last_date = ? WHERE user_id = ? AND job_income_id = ?'
                        db_cmd(cmd,(job['last_date']-0.25, USER_ID, job['job_income_id']))
                        print(f"Now trying to reduce {usr}'s last date to {last_date-0.25}!")
                    start_date = last_date + 0.25 # adjust start_date for next income
        self.param_vals, _ = load_params()

    def save_from_flask(self, form: dict[str,str]):
        """Save the form results into the database.

        Args:
            form (dict[str,str]): (param:str(value))
        """
        form_set = set()
        for k,v in form.items(): 
            if k in form_set: continue # avoid duplicates from checkboxes. Only the first should be counted
            else: form_set.add(k)
            if v.isdigit(): 
                v = int(v)
            elif _is_float(v):
                v = float(v)
            elif v == "True":
                v = 1
            elif v == "False":
                v = 0
                
            if k in self.param_vals: # the key matches the db name exactly, therefore isn't a special key
                cmd = f'UPDATE users SET {k} = ? WHERE user_id = ?' # Can't use SQL objects as placeholders https://stackoverflow.com/a/25387570/13627745
                db_cmd(cmd,(v,USER_ID))
                continue
            else:
                try: k, idx, sub_k = k.split('@')
                except: k, idx = k.split('@')
            # job incomes
            if k in ['user_jobs','partner_jobs']:
                cmd = f'UPDATE job_incomes SET {sub_k} = ? WHERE user_id = ? AND job_income_id = ?'
            # kid birth years
            elif k == 'kid_birth_years':
                cmd = f'UPDATE kids SET birth_year = ? WHERE user_id = ? AND kid_id = ?'
            # earnings record
            elif k in ['user_earnings_record','partner_earnings_record']:
                cmd = f'UPDATE earnings_records SET {sub_k} = ? WHERE user_id = ? AND earnings_id = ?' 
            db_cmd(cmd,(v,USER_ID,idx))
        self.param_vals, _ = load_params()
            
def load_params():
    """Pulls parameter values from the SQL DB, then pulls parameter details from the param_detail.json file

    Returns:
        dict: param_vals = {param:val} \n
        dict: param_details = {param:detail object}
    """
    res, headers = db_cmd(db.text(f'SELECT * FROM users WHERE user_id == {USER_ID}'))
    param_vals = {param:value for param, value in zip(headers,res[0])}
    del param_vals['user_id'] # not needed and doesn't have a match in param_details
        # historic earnings for social security
    usr_earnings, _ = db_cmd(db.text(f'SELECT * from earnings_records WHERE user_id == {USER_ID} AND is_partner_earnings == 0'))
    partner_earnings, _ = db_cmd(db.text(f'SELECT * from earnings_records WHERE user_id == {USER_ID} AND is_partner_earnings == 1'))
    param_vals['user_earnings_record'] = [[idx,year,earnings] for idx,_,_,year,earnings in usr_earnings]
    param_vals['partner_earnings_record'] = [[idx,year,earnings] for idx,_,_,year,earnings in partner_earnings]
        # kid birth years
    birth_years, _ = db_cmd(db.text(f'SELECT * from kids WHERE user_id == {USER_ID}'))
    param_vals['kid_birth_years'] = [[idx,year] for idx,_,year in birth_years]
        # income from jobs
    usr_job_incomes, descriptions = db_cmd(db.text(f'SELECT * from job_incomes WHERE user_id == {USER_ID} AND is_partner_income == 0'))
    partner_job_incomes, _ = db_cmd(db.text(f'SELECT * from job_incomes WHERE user_id == {USER_ID} AND is_partner_income == 1'))
            # Using a dict comprehension (to get sub-parameters) in a list comprehension (to get all jobs)
    param_vals['user_jobs'] = [{key:val for key,val in zip(descriptions,job) if key not in {'user_id','is_partner_income'}} \
                            for job in usr_job_incomes] 
    param_vals['partner_jobs'] = [{key:val for key,val in zip(descriptions,job) if key not in {'user_id','is_partner_income'}} \
                            for job in partner_job_incomes]
    # get param details
    with open(const.PARAM_DETAILS_LOC) as json_file:
        param_details:dict = json.load(json_file)
    return param_vals, param_details

def db_cmd(cmd,cmd_args:tuple=None):
    """Provide the query result to the provided command string

    Args:
        sql_cmd (_Executable): SQLAlchemy statement that can be executed
        cmd_args (tuple): Any arguements that need to be passed into the sql_cmd

    Returns:
        list: all output rows from query \n
        list: column names
    """
    with ENGINE.connect() as conn:
        if cmd_args: # Used to avoid SQL injection attacks
            res = conn.execute(cmd,cmd_args)
        else:
            res = conn.execute(cmd)
            return res.fetchall(), res.keys() # when cmd_args aren't used, it's for a SELECT command. If you try to return for an UPDATE command, it'll crash
    
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