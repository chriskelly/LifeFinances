import json
from pathlib import Path
script_location = Path(__file__).absolute().parent
params_values_location = script_location / 'params.json'

with open(params_values_location) as json_file:
    params = json.load(json_file)
    
print(params)

def save_params(params:dict):
    """Overwrite params.json with passed-in dict"""
    with open(params_values_location, 'w') as outfile:
        json.dump(params, outfile,indent=4)