import json
# had issues with params file location between windows and macOS
from pathlib import Path
script_location = Path(__file__).absolute().parent
params_location = script_location / 'params.json'


class Model:
    def __init__(self):
        with open(params_location) as json_file:
            self.params = json.load(json_file)

    def save_params(self,params:dict):
        with open(params_location, 'w') as outfile:
            json.dump(params, outfile,indent=4)
            
    def run_calcs(self,params:dict):
        params = self._clean_data(params)
        params["Domestic Proportion"]=1-params["International Proportion"]
        return params

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
        
