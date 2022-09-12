import  copy
from simulator import Simulator
import simulator
from models.model import Model
import numpy as np 

TRIALS = 30
RUN_QTYS = [100,200,500,1000,2000,3000,4000,5000,7000,10000]

simulator.DEBUG_LVL = 0

model = Model()
full_params = copy.deepcopy(model.params) 
for runs in RUN_QTYS:
    param_vals = {key:obj["val"] for (key,obj) in full_params.items()}
    override_dict = {'monte_carlo_runs' : runs }
    new_simulator = Simulator(param_vals,override_dict)
    rates = []
    for _ in range(TRIALS):
        success_rate, _= new_simulator.main()
        rates.append(success_rate)
    print(f'Runs: {runs} | Range: {np.ptp(rates)*100:.2f}%')