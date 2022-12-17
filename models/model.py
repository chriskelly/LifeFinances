import shutil, copy, json
import data.constants as const

def update_dicts(up_to_date:dict,out_of_date:dict) -> dict:
    """Temporarily stores values and range of out_of_date dict, then creates copy of up_to_date dict, but over-writes vals and ranges.

    Parameters
    ----------
    up_to_date : dict
        DESCRIPTION.
    out_of_date : dict
        DESCRIPTION.

    Returns
    -------
    Updated Dict.

    """
    temp_param_val = {k:v["val"] for k,v in out_of_date.items()} # save all the old vals
    temp_param_range = {k:v["range"] for k,v in out_of_date.items() if ("range" in v)} # save all the old vals
    del temp_param_val["Version"]
    updated_dict = copy.deepcopy(up_to_date) # deepcopy to avoid referencing the same dict
    for key in updated_dict.keys():
        if key in temp_param_val:
            updated_dict[key]['val'] = temp_param_val[key] # replace copied val
        if key in temp_param_range:
            updated_dict[key]['range'] = temp_param_range[key]
    print('Parameters Updated')
    return updated_dict

def load_params() -> dict:
    """Checks that params is up-to-date, then returns params.
    If params or default_params out of date, will update the out-of-date json 
    and save it.

    Returns
    -------
    params : dict
        DESCRIPTION.

    """
    try:
        with open(const.PARAMS_LOC) as json_file:
            params = json.load(json_file)
    except: # needed for the first time code is run
        shutil.copy(const.DEFAULT_PARAMS_LOC, const.PARAMS_LOC)
        with open(const.PARAMS_LOC) as json_file:
            params = json.load(json_file)
    with open(const.DEFAULT_PARAMS_LOC) as json_file:
        default_params = json.load(json_file)
    if float(params['Version']['val']) > float(default_params['Version']['val']):
        default_params = update_dicts(up_to_date=params, out_of_date=default_params)
        with open(const.DEFAULT_PARAMS_LOC, 'w') as outfile:
            json.dump(default_params, outfile, indent=4)
    if float(default_params['Version']['val']) > float(params['Version']['val']):
        params = update_dicts(up_to_date=default_params, out_of_date=params)
        with open(const.PARAMS_LOC, 'w') as outfile:
            json.dump(params, outfile, indent=4)
    return params

class Model:
    """
    An instance of Model is used to keep track of a collection of parameters
    
    Attributes
    ----------
    params : dict
        Named parameters that contribute to financial calculations
    
    """
    def __init__(self):
        self.params = load_params()

    def save_params(self, params_vals: dict):
        """Overwrite params.json with passed-in params_vals dict"""
        for param, obj in self.params.items():
            obj["val"] = params_vals[param]
        with open(const.PARAMS_LOC, 'w') as outfile:
            json.dump(self.params, outfile, indent=4)

    def run_calcs(self, params_vals: dict):
        """Cleans data to correct format and runs all calculations, 
        updating the param:val dict passed-in and returning the updated dict"""
        params_vals = clean_data(params_vals)
        calcd_params = self.filter_params(include=True,attr="calcd")
        for param,obj in calcd_params.items():
            params_vals[param] = eval(obj["calcd"]) # evaluate string saved in self.params under "calcd"
        return params_vals

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

def clean_data(params: dict):
    for k, v in params.items():
        try:
            if v.isdigit():
                params[k] = int(v)
            elif _is_float(v):
                params[k] = float(v)
            elif v == "True":
                params[k] = True
            elif v == "False":
                params[k] = False
        except:
            continue
    return params

"""Naively looks through params.json - searches for false and true flags expressed as strings and un-stringifies them"""
def Validate_ParamsJSON(configFile):
    Jsontxt = []
    with open(configFile,'r+') as f:
        Jsontxtorig = f.readlines()
        for l in Jsontxtorig:
           new = l.replace('\"False\"','false').replace('\"True\"','true')
           Jsontxt.append(new)

    with open(configFile,'w') as f:
        f.writelines(Jsontxt)

#This executes whenever model.py is loaded as a module. Automatically fix JSON naming.    
try:
    Validate_ParamsJSON(const.PARAMS_LOC)
    Validate_ParamsJSON(const.DEFAULT_PARAMS_LOC)
    Validate_ParamsJSON(const.PARAMS_SUCCESS_LOC)
except Exception as e:
    print("Warning validating params.json - {}".format(e))