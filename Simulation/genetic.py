from simulator import Simulator
import simulator
from model import Model
import numpy as np
import random
import copy

class Algorithm:
    def __init__(self):
        self.model = Model()
        simulator.DEBUG_LVL = 0
    
    
    # ---------------------- Initialization ---------------------- #
    def main(self):
        params = copy.deepcopy(self.model.params) # make a copy rather than point to the same dict # https://stackoverflow.com/a/22341377/13627745
        mutable_params = self.model.filter_params(include=True, attr='range')
        success_rate = 0.0
        while success_rate <  1.0:
            mutable_params = self._mutate(mutable_params)
            params.update(mutable_params)
            param_vals = {key:obj["val"] for (key,obj) in params.items()}
            new_simulator = Simulator(param_vals)
            success_rate = new_simulator.main()
            test =0
        
        
    
    # Seeded option and random option

        
        debug_point = True
    
    # ---------------------- Mutation ---------------------- #
    def _mutate(self,params):
        new_dict = copy.deepcopy(params) 
        for param,obj in new_dict.items():
            new_dict[param]['val'] = str(random.choice(eval(obj["range"])))
        return new_dict
    
    
    
    # ---------------------- Crossover ---------------------- #
    
    
    # ---------------------- Selection ---------------------- #
    
    
    
    
        
    
if __name__ == '__main__':
    algorithm = Algorithm()
    algorithm.main()