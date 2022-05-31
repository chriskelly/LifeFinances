import json
# had issues with params file location between windows and macOS
from pathlib import Path
script_location = Path(__file__).absolute().parent
params_values_location = script_location / 'params.json'


class Model:
    def __init__(self):
        with open(params_values_location) as json_file:
            self.params = json.load(json_file)

    def save_params(self, params_vals: dict):
        """Overwrite params.json with passed-in params_vals dict"""
        for param, obj in self.params.items():
            obj["val"] = params_vals[param]
        with open(params_values_location, 'w') as outfile:
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
            elif v == "True" or v == "False":
                params[k] = bool(v)
        return params

    def _is_float(self, element: any):
        try:
            float(element)
            return True
        except ValueError:
            return False
