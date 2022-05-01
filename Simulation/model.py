import json
from pathlib import Path
script_location = Path(__file__).absolute().parent
params_location = script_location / 'params.json'


class Model:
    def __init__(self):
        with open(params_location) as json_file:
            self.param_vals = json.load(json_file)

    def save_params(self,param_vals):
        with open(params_location, 'w') as outfile:
            json.dump(param_vals, outfile,indent=4)
            
    def sum_yearly_budget(self,monthly_list,yearly_list):
        return sum([12*n for n in monthly_list])+sum(yearly_list)