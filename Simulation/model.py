import json
# had issues with params file location between windows and macOS
from pathlib import Path
script_location = Path(__file__).absolute().parent
params_values_location = script_location / 'params.json'


class Model:
    def __init__(self):
        with open(params_values_location) as json_file:
            self.params = json.load(json_file)

    def save_params(self,params_vals:dict):
        """Overwrite params.json with passed-in params_vals dict"""
        for k,obj in self.params.items():
            obj["val"] = params_vals[k]
        with open(params_values_location, 'w') as outfile:
            json.dump(self.params, outfile,indent=4)
            
    def run_calcs(self,params_vals:dict):
        """Cleans data to correct format and runs all calculations, 
        updating the dict passed-in and returning the updated dict"""
        params_vals = self._clean_data(params_vals)
        params_vals["Domestic Proportion"]=1-params_vals["International Proportion"]
        return params_vals
    
    def check_attr(self,param:str,attr:str):
        pass

    def _clean_data(self,params:dict):
        for k,v in params.items():
            if v.isdigit():
                params[k]=int(v)
            elif self._is_float(v):
                params[k]=float(v)
            elif v == "True" or v == "False":
                params[k]=bool(v)
        return params

    def _is_float(self,element:any):
        try:
            float(element)
            return True
        except ValueError:
            return False
        
