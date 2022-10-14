import json
import data.constants as const

def update_dicts(up_to_date:dict,out_of_date:dict):
    """Looks for new keys added or keys removed from the most recently updated dict. 
    Copys over new keys to old dict and removes keys not found in the updated version."""
    for key in up_to_date.keys():
        if key not in out_of_date:
            out_of_date[key] = up_to_date[key]
    del_keys = [] # needed since you can't delete keys while iterating through
    for key in out_of_date.keys():
        if key not in up_to_date:
            del_keys.append(key)
    for key in del_keys:
        del out_of_date[key]
    out_of_date['Version']['val'] = up_to_date['Version']['val']
    print('Parameters Updated')
    # doesn't need to return since the dicts are directly modified

def load_params() -> dict:
    """Checks that params is up-to-date, then returns params.
    If params or default_params out of date, will update the out-of-date json and save it."""
    try:
        with open(const.PARAMS_LOC) as json_file:
            params = json.load(json_file)
        with open(const.DEFAULT_PARAMS_LOC) as json_file:
            default_params = json.load(json_file)
    except:
        raise Exception('Parameter file not found. Copy from /data/default_params and place in /data folder.')
    if float(params['Version']['val']) > float(default_params['Version']['val']):
        update_dicts(up_to_date=params, out_of_date=default_params)
        with open(const.DEFAULT_PARAMS_LOC, 'w') as outfile:
            json.dump(default_params, outfile, indent=4)
    if float(default_params['Version']['val']) > float(params['Version']['val']):
        update_dicts(up_to_date=default_params, out_of_date=params)
        with open(const.PARAMS_LOC, 'w') as outfile:
            json.dump(params, outfile, indent=4)
    return params

class Model:
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
        params_vals = self._clean_data(params_vals)
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

    def _clean_data(self, params: dict):
        for k, v in params.items():
            if type(v) is dict: # used for Denica pension parameter
                continue
            elif v.isdigit():
                params[k] = int(v)
            elif self._is_float(v):
                params[k] = float(v)
            elif v == "True":
                params[k] = True
            elif v == "False":
                params[k] = False
        return params

    def _is_float(self, element: any):
        try:
            float(element)
            return True
        except ValueError:
            return False
