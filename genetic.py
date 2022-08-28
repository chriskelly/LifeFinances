import random, copy, math, json
from logging import exception
from simulator import Simulator
import simulator
from models.model import Model
import data.constants as const
import numpy as np # used in eval() of parameter ranges
import scipy.stats as ss

RESET_SUCCESS = False
SEEDED = False
SUCCESS_THRESH = 0.5
OFFSPRING_QTY = 2
TARGET_SUCCESS_RATE = 0.95
ITER_LIMIT = 10 # Max number of times to run if parent is better than all children

class Algorithm:
    def __init__(self):
        self.model = Model()
        simulator.DEBUG_LVL = 0
        with open(const.PARAMS_SUCCESS_LOC) as json_file:
            self.param_cnt = json.load(json_file)
        if RESET_SUCCESS: self.param_cnt = {}
    
    # ---------------------- Initialization ---------------------- #
    def main(self):
        full_params = copy.deepcopy(self.model.params) # make a copy rather than point to the same dict # https://stackoverflow.com/a/22341377/13627745
        mutable_params = self.model.filter_params(include=True, attr='range')
        success_rate = 0.0
        parent_is_best_qty = 0
        if SEEDED:
            pass
        else: 
            while success_rate <  SUCCESS_THRESH:
                success_rate, parent_mute_params = self._make_child(full_params,mutable_params,mutate='random')
                print(f"Success Rate: {success_rate*100:.2f}%")
        # Plot first parameters
        self._update_param_count(mutable_params,first_time=True)
        while success_rate <  TARGET_SUCCESS_RATE:
            # Make children
            children = []
            for _ in range(OFFSPRING_QTY):
                children.append(self._make_child(full_params,parent_mute_params,mutate='step',max_step=max(1,parent_is_best_qty)))
            # Breed from best child (or parent if all children worse)
            children.sort(key=lambda u: u[0], reverse=True) # Needed to avoid it sorting by the params if success rates are equal
            # Compare parent to best child
            if success_rate >= children[0][0]: # Parent better than child
                parent_is_best_qty += 1
                print(f"No better children {parent_is_best_qty}/10")
                if parent_is_best_qty >= ITER_LIMIT: # if children not improving, start over with random child
                    param_vals = {key:obj["val"] for (key,obj) in parent_mute_params.items()}
                    print(f"Local max: {success_rate*100:.2f}%\n {param_vals}")
                    parent_is_best_qty = 0
                    success_rate = 0.0
                    while success_rate <  SUCCESS_THRESH:
                        success_rate, parent_mute_params = self._make_child(full_params,mutable_params,mutate='random')
            else: # If child better than parent, update success rate and params
                parent_is_best_qty = 0
                success_rate, parent_mute_params = children[0] 
                self._update_param_count(parent_mute_params)
                print(f"Success Rate: {success_rate*100:.2f}%")
            # If child meets target, test the results to the max before ending routine
            if success_rate >= TARGET_SUCCESS_RATE: 
                current_monte_carlo_runs = simulator.MONTE_CARLO_RUNS # save previous value
                simulator.MONTE_CARLO_RUNS = 5000
                success_rate = self._make_child(full_params,parent_mute_params,mutate='none')[0] # test at higher monte carlo runs
                if success_rate < TARGET_SUCCESS_RATE: 
                    print(f"Couldn't stand the pressure...{success_rate*100:.2f}%")
                else:
                    param_vals = {key:obj["val"] for (key,obj) in parent_mute_params.items()} 
                    print(f"Final max: {success_rate*100:.2f}%\n {param_vals}")
                simulator.MONTE_CARLO_RUNS = current_monte_carlo_runs
                
        debug_point = True
    
    # ---------------------- Mutation ---------------------- #
    def _random_mutate(self,mutable_params):
        new_dict = copy.deepcopy(mutable_params) 
        for param,obj in new_dict.items():
            new_dict[param]['val'] = str(random.choice(eval(obj["range"])))
        return new_dict
    
    def _step_mutate(self,mutable_params,max_step=1):
        new_dict = copy.deepcopy(mutable_params)
        for param,obj in new_dict.items():
            ls = list(eval(obj["range"]))
            val = obj['val'] if not self.model._is_float(obj['val']) else float(obj['val'])
            old_position = ls.index(val)
            length = len(ls)
            new_position = random.randint(max(0,old_position - max_step),min(length-1,old_position + max_step))
            new_dict[param]['val'] = str(ls[new_position])
        return new_dict
    
    
    # ---------------------- Crossover ---------------------- #
    
    
    # ---------------------- Selection ---------------------- #
    
    
    
    # -------------------------------- HELPER FUNCTIONS -------------------------------- #
    def _update_param_count(self,mutable_params:dict,first_time=False):
        if RESET_SUCCESS and first_time:
            for param,obj in mutable_params.items():
                self.param_cnt[param] = {}
                for option in eval(obj["range"]):
                    self.param_cnt[param][str(option)] = 0
        for param,obj in mutable_params.items():
                for option in eval(obj["range"]):
                    if str(option) == obj['val']:
                        self.param_cnt[param][str(option)] += 1
        with open(const.PARAMS_SUCCESS_LOC, 'w') as outfile:
            json.dump(self.param_cnt, outfile, indent=4)
    
    def _make_child(self,full_params:dict, parent_mute_params:dict,mutate:str,max_step:int=1):
        """Returns a tuple (success rate, mutable_params).\n
        Mutate can be 'step', 'random', or 'none'"""
        if mutate == 'step':
            child_mute_params = self._step_mutate(parent_mute_params,max_step=max_step) 
        elif mutate == 'random':
            child_mute_params = self._random_mutate(parent_mute_params)
        elif mutate == 'none':
            child_mute_params = parent_mute_params
        else: exception('no valid mutation chosen')
        full_params.update(child_mute_params)
        param_vals = {key:obj["val"] for (key,obj) in full_params.items()}
        new_simulator = Simulator(param_vals)
        child_success_rate = new_simulator.main()
        return (child_success_rate,child_mute_params)
    
        
    
if __name__ == '__main__':
    algorithm = Algorithm()
    algorithm.main()