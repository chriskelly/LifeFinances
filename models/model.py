import shutil, copy, json, sqlite3, contextlib
import data.constants as const

# def update_dicts(up_to_date:dict,out_of_date:dict) -> dict:
#     """Temporarily stores values and range of out_of_date dict, then creates copy of up_to_date dict, but over-writes vals and ranges.

#     Parameters
#     ----------
#     up_to_date : dict
#         DESCRIPTION.
#     out_of_date : dict
#         DESCRIPTION.

#     Returns
#     -------
#     Updated Dict.

#     """
#     temp_param_val = {k:v["val"] for k,v in out_of_date.items()} # save all the old vals
#     temp_param_range = {k:v["range"] for k,v in out_of_date.items() if ("range" in v)} # save all the old vals
#     del temp_param_val["Version"]
#     updated_dict = copy.deepcopy(up_to_date) # deepcopy to avoid referencing the same dict
#     for key in updated_dict.keys():
#         if key in temp_param_val:
#             updated_dict[key]['val'] = temp_param_val[key] # replace copied val
#         if key in temp_param_range:
#             updated_dict[key]['range'] = temp_param_range[key]
#     print('Parameters Updated')
#     return updated_dict

def load_params():
    """Pulls parameter values from the SQL DB, then pulls parameter details from the param_detail.json file

    Returns:
        dict: param_vals = {param:val} \n
        dict: param_details = {param:detail object}
    """
    user_id = 1 # Default ID is 1
    user_cmd = f'SELECT * FROM users WHERE user_id == {user_id}'
    values, descriptions = db_query(user_cmd)
    param_vals = {description[0]:value for description, value in zip(descriptions[1:],values[0][1:])}
        # historic earnings for social security
    usr_earnings_cmd = f'SELECT * from earnings_records WHERE user_id == {user_id} AND is_partner_earnings == 0'
    partner_earnings_cmd = usr_earnings_cmd[:-1]+'1' # look for is_partner_earnings == 1
    usr_earnings, _ = db_query(usr_earnings_cmd)
    partner_earnings, _ = db_query(partner_earnings_cmd)
    year_idx, earnings_idx = 3, 4
    param_vals['user_earnings_record'] = {entry[year_idx]:entry[earnings_idx] for entry in usr_earnings}
    param_vals['partner_earnings_record'] = {entry[year_idx]:entry[earnings_idx] for entry in partner_earnings}
        # kid birth years
    birth_years, _ = db_query(sql_cmd=f'SELECT * from kids WHERE user_id == {user_id}')
    param_vals['kid_birth_years'] = [entry[2] for entry in birth_years]
        # income from jobs
    usr_job_incomes_cmd = f'SELECT * from job_incomes WHERE user_id == {user_id} AND is_partner_income == 0'
    partner_job_incomes_cmd = usr_job_incomes_cmd[:-1]+'1' # look for is_partner_income == 1
    usr_job_incomes, descriptions = db_query(usr_job_incomes_cmd)
    partner_job_incomes, _ = db_query(partner_job_incomes_cmd)
            # Using a dict comprehension (to get sub-parameters) in a list comprehension (to get all jobs)
    param_vals['user_jobs'] = [{key[0]:val for key,val in zip(descriptions[3:],job[3:])} \
                            for job in usr_job_incomes] # 3 is the first index that isn't an ID or partner check
    param_vals['partner_jobs'] = [{key[0]:val for key,val in zip(descriptions[3:],job[3:])} \
                            for job in partner_job_incomes]
    # get param details
    with open(const.PARAM_DETAILS_LOC) as json_file:
        param_details:dict = json.load(json_file)
    return param_vals, param_details
    
    # try:
    #     with open(const.PARAM_DETAILS_LOC) as json_file:
    #         params = json.load(json_file)
    # except: # needed for the first time code is run
    #     shutil.copy(const.DEFAULT_PARAMS_LOC, const.PARAM_DETAILS_LOC)
    #     with open(const.PARAM_DETAILS_LOC) as json_file:
    #         params = json.load(json_file)
    # with open(const.DEFAULT_PARAMS_LOC) as json_file:
    #     default_params = json.load(json_file)
    # if float(params['Version']['val']) > float(default_params['Version']['val']):
    #     default_params = update_dicts(up_to_date=params, out_of_date=default_params)
    #     with open(const.DEFAULT_PARAMS_LOC, 'w') as outfile:
    #         json.dump(default_params, outfile, indent=4)
    # if float(default_params['Version']['val']) > float(params['Version']['val']):
    #     params = update_dicts(up_to_date=default_params, out_of_date=params)
    #     with open(const.PARAM_DETAILS_LOC, 'w') as outfile:
    #         json.dump(params, outfile, indent=4)
    # return params

class Model:
    """
    An instance of Model is used to keep track of a collection of parameters
    
    Attributes
    ----------
    params : dict
        Named parameters that contribute to financial calculations
    
    """
    def __init__(self):
        self.param_vals, self.param_details = load_params()

    def save_params(self, params_vals: dict):
        """Overwrite params.json with passed-in params_vals dict"""
        raise Exception('save param method not updated')
        # params_vals = clean_data(params_vals)
        # for param, obj in self.params.items():
        #     obj["val"] = params_vals[param]
        # with open(const.PARAM_DETAILS_LOC, 'w') as outfile:
        #     json.dump(self.params, outfile, indent=4)

    def filter_params(self, include: bool, attr: str, attr_val: any = None):
        """returns dict with params that include/exclude specified attributes
        and optional specified attribute values"""
        new_dict = {}
        for (param, obj) in self.params.items():
            if include:
                if attr in obj:
                    if attr_val is None:
                        new_dict[param] = obj  # param matches just attr
                    elif obj[attr] == attr_val:
                        # param matches attr and attr_val
                        new_dict[param] = obj
            else:  # exclude
                if attr not in obj:
                    new_dict[param] = obj  # param does not include attr
                elif attr_val is None:
                    continue
                elif obj[attr] != attr_val:
                    # param does not match specific attr_val
                    new_dict[param] = obj
        return new_dict

def db_query(sql_cmd:str):
    """Provide the query result to the provided command string

    Args:
        sql_cmd (str): SQL command string

    Returns:
        list: all output rows from query \n
        tuple: description objects with the column names in first position of each item
    """
    # check for database not in data folder yet
    try: 
        with open(const.DB_LOC): pass 
    except FileNotFoundError:
        shutil.copy(const.DEFAULT_DB_LOC, const.DB_LOC)
        return db_query(sql_cmd)
    
    with contextlib.closing(sqlite3.connect(const.DB_LOC)) as con, con,  \
            contextlib.closing(con.cursor()) as cursor:
        cursor.execute(sql_cmd)
        return cursor.fetchall(), cursor.description
    

def _is_float(element):
    """
    Checks whether the element can be converted to a float

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

def clean_data(param_vals: dict):
    for k, v in param_vals.items():
        try:
            if v.isdigit():
                param_vals[k] = int(v)
            elif _is_float(v):
                param_vals[k] = float(v)
            elif v == "True":
                param_vals[k] = True
            elif v == "False":
                param_vals[k] = False
        except:
            continue
    return param_vals