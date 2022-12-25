import random, copy, math, json
from simulator import Simulator
import simulator
import models.model
from models.model import Model
import data.constants as const
import numpy as np # used in eval() of parameter ranges
import scipy.stats as ss
import time

DEBUG_LVL = 2 # Lvl 0 shows only local and final max param sets
RESET_SUCCESS = False # Set to true to reset all the counts in param_success.json
SUCCESS_THRESH = 0.5 # Initial threshold for random mutations to beat before switching to step mutations
OFFSPRING_QTY = 10
TARGET_SUCCESS_RATE = 0.95
INITIAL_MONTE_RUNS = 100
MAX_MONTE_RUNS = 5000
ITER_LIMIT = 5 # Max number of times to run if parent is better than all children
SEED = False # Use current params to start with
RNG = np.random.default_rng()

class Algorithm:
    def __init__(self):
        self.reset_success = RESET_SUCCESS
        simulator.DEBUG_LVL = 0
        if self.reset_success: 
            self.param_cnt = {}
        else:
            self._load_param_success()
    
    def main(self, next_loop=(False,[])):
    # ---------------------- First parameter set ---------------------- #
        self.model = Model()
        mutable_params = self.model.filter_params(include=True, attr='range')
        self.prev_used_params = [] # used to track and prevent reusing the same param sets during step mutation
        success_rate, parent_is_best_qty = 0.0 , 0
        if next_loop[0]: # check to see if this is the first loop or if the previous one was successful and we're auto-advancing
            full_params = next_loop[1]
            parent_mute_params = mutable_params
        elif SEED: 
            full_params = copy.deepcopy(self.model.params) # make a copy rather than point to the same dict # https://stackoverflow.com/a/22341377/13627745
            parent_mute_params = mutable_params
        else: # if not, keep random mutating till we hit SUCCESS_THRESH
            full_params = copy.deepcopy(self.model.params) # make a copy rather than point to the same dict # https://stackoverflow.com/a/22341377/13627745
            while success_rate <  SUCCESS_THRESH:
                success_rate, parent_mute_params = self._make_child(full_params,mutable_params,success_rate,mutate='random')
                if DEBUG_LVL>=1: print(f"Success Rate: {success_rate*100:.2f}%")
        self._update_param_count(mutable_params,first_time=True)
    # ---------------------- Improvement loop ---------------------- #
        while True: # while success_rate <  TARGET_SUCCESS_RATE      if you every want to stop the auto-advance
            # Confirm if other cores have succeeded yet or not
            self._check_if_beaten(full_params)
            # Make children
            children = []
            for idx in range(OFFSPRING_QTY):
                #TODO: #62 Make a progress loading bar in the terminal for offspring
                children.append(self._make_child(full_params,parent_mute_params,success_rate,mutate='step',
                                                 max_step=max(1,parent_is_best_qty),idx=idx))
            # Find best child (or use parent if all children worse)
            children.sort(key=lambda u: u[0], reverse=True) # Needed to avoid it sorting by the params if success rates are equal
            # ------ Children not improving ------ #
            if success_rate >= children[0][0]: # Parent better than child
                parent_is_best_qty += 1
                if DEBUG_LVL>=1: print(f"No better children {parent_is_best_qty}/{ITER_LIMIT}")
                if parent_is_best_qty >= ITER_LIMIT: # if children not improving, start over with random child
                    param_vals = {key:obj["val"] for (key,obj) in parent_mute_params.items()}
                    print(f"Local max: {success_rate*100:.2f}%\n {param_vals}")
                    parent_is_best_qty = 0
                    success_rate = 0.0
                    while success_rate <  SUCCESS_THRESH:
                        success_rate, parent_mute_params = self._make_child(full_params,mutable_params,success_rate,mutate='random')
            # ------ Child is better ------ #
            else: # If child better than parent, update success rate and params
                parent_is_best_qty = 0
                success_rate, parent_mute_params = children[0] 
                self._update_param_count(parent_mute_params)
                if DEBUG_LVL>=1: print(f"Success Rate: {success_rate*100:.2f}%")
            # ------ Child beats target, proceed to test child ------ #
            if success_rate >= TARGET_SUCCESS_RATE * 1.005: # Add a slight buffer to prevent osccilating between barely beating it and failing upon retest 
                current_monte_carlo_runs = simulator.MONTE_CARLO_RUNS # save previous value
                simulator.MONTE_CARLO_RUNS = MAX_MONTE_RUNS
                success_rate = self._make_child(full_params,parent_mute_params,success_rate,mutate='none')[0] # test at higher monte carlo runs
                simulator.MONTE_CARLO_RUNS = current_monte_carlo_runs
                if success_rate < TARGET_SUCCESS_RATE: 
                    if DEBUG_LVL>=1:
                        print(f"Couldn't stand the pressure...{success_rate*100:.2f}%")
                else: # Print results, overwrite params, start again with more ambitious FI target date
                    param_vals = {key:obj["val"] for (key,obj) in parent_mute_params.items()}
                    self._check_if_beaten(full_params)
                    print(f"Final max: {success_rate*100:.2f}%\n {param_vals}")
                    full_params.update(parent_mute_params)
                    with open(const.PARAMS_LOC, 'w') as outfile:
                        json.dump(full_params, outfile, indent=4)
                    # Reduce all last dates by one quarter
                        # Assuming dates for bond tent also needs to be reduced with earlier retire date
                    full_params["Bond Tent Start Date"]['val'] -= 0.25
                    full_params["Bond Tent Peak Date"]['val'] -= 0.25 
                    full_params["Bond Tent End Date"]['val'] -= 0.25 
                        # Reduce income stop dates
                    for usr in ['User','Partner']:
                        start_date = simulator.TODAY_YR_QT
                        for i, income in enumerate(full_params[f'{usr} Incomes']['val']):
                            # get info on this income
                            last_date = income['Last Date']
                            duration = last_date - start_date + 0.25
                            reduce = bool(income['Try to Reduce'])
                            if duration <= 0.25 and reduce: # check if job will start before previous job ends
                                raise Exception(f'Income with Last Date of {income["Last Date"]} ends too early') # Not sure how to better handle this. You could delete the income item in the params, but I don't think users would prefer the income be deleted. You could add some sort of skip tag to the income that income.py then uses to ignore, but that may not be easily debuggable
                            if reduce: 
                                # reduce the last_date and update full_params
                                last_date -= 0.25
                                full_params[f'{usr} Incomes']['val'][i]['Last Date'] = last_date
                                print(f"Now trying to reduce {usr}'s last date to {last_date}!")
                            start_date = last_date + 0.25 # adjust start_date for next income
                    self.main(next_loop=(True,full_params))
                    
    # ---------------------- Mutation ---------------------- #
    def _random_mutate(self,mutable_params:dict) -> dict:
        """Return mutable params with shuffled values"""
        new_dict = copy.deepcopy(mutable_params) 
        for param,obj in new_dict.items():
            new_dict[param]['val'] = str(random.choice(eval(str(obj["range"]))))
        return new_dict
    
    def _step_mutate(self,mutable_params:dict,max_step=1) -> dict:
        """Return mutable params with values shifted in a normal distribution around 
        provided mutable_param values with a max deviation of max_step"""
        new_dict = copy.deepcopy(mutable_params)
        for param,obj in new_dict.items():
            ls = list(eval(str(obj["range"])))
            val = obj['val'] if not models.model._is_float(obj['val']) else float(obj['val'])
            old_idx = ls.index(val)
            new_idx = min(len(ls)-1,max(0,self._gaussian_int(center=old_idx,max_deviation=max_step)))
            new_dict[param]['val'] = str(ls[new_idx])
        if new_dict in self.prev_used_params:
            print(f'Tried params: {len(self.prev_used_params)}')
            new_dict = self._step_mutate(mutable_params,max_step)
        return new_dict
    
    # -------------------------------- HELPER FUNCTIONS -------------------------------- #
    def _load_param_success(self):
        """Load from json file and update self.param_cnt.
        If it fails, dumps an empty json file.
        """
        with open(const.PARAMS_SUCCESS_LOC, 'r+') as json_file:
                try:
                    self.param_cnt = json.load(json_file)
                except: 
                    self.param_cnt = {}
                    self.reset_success = True
                    json.dump(self.param_cnt, json_file, indent=4)
    
    def _check_if_beaten(self,full_params):
        for usr in ['User','Partner']:
            for i, income in enumerate(full_params[f'{usr} Incomes']['val']):
                if income["Last Date"] > models.model.load_params()[f'{usr} Incomes']['val'][i]["Last Date"]:
                    print('got beat')
                    self.main() # start over with the new successful params.json if another core figured it out
    
    def _gaussian_int(self,center:int,max_deviation:int) -> int: # credit: https://stackoverflow.com/questions/37411633/how-to-generate-a-random-normal-distribution-of-integers
        """Returns an int from a random gaussian distribution"""
        scale= max_deviation/1.5 # decreasing the demonimator results in a flater distribution
        x = np.arange(-max_deviation, max_deviation+1) +center
        xU, xL = x + 0.5, x - 0.5
        prob = ss.norm.cdf(xU,loc=center, scale = scale) - ss.norm.cdf(xL,loc=center, scale = scale)
        prob = prob / prob.sum() # normalize the probabilities so their sum is 1
        return np.random.choice(x, p = prob)
    
    def _update_param_count(self,mutable_params:dict,first_time=False):
        """Edit the param_success.json file to add another tally for each of the 
        successful mutable_param values. If first time and RESET_SUCCESS, 
        overwrite previous file and set count to 0"""
        self._load_param_success()
        if self.reset_success and first_time:
            for param,obj in mutable_params.items():
                self.param_cnt[param] = {}
                for option in eval(str(obj["range"])):
                    self.param_cnt[param][str(option)] = 0
        for param,obj in mutable_params.items():
                for option in eval(str(obj["range"])):
                    if str(option) == obj['val']:
                        self.param_cnt[param][str(option)] += 1
        with open(const.PARAMS_SUCCESS_LOC, 'w') as outfile:
            json.dump(self.param_cnt, outfile, indent=4)
    
    def _make_child(self,full_params:dict, parent_mute_params:dict,success_rate:float,mutate:str,max_step:int=1,idx:int=0):
        """Returns a tuple (success rate, mutable_params).\n
        Mutate can be 'step', 'random', or 'none'"""
        child_Start_Time = time.time()
        if mutate == 'step':
            child_mute_params = self._step_mutate(parent_mute_params,max_step=max_step) 
            self.prev_used_params.append(child_mute_params)
        elif mutate == 'random':
            self.prev_used_params = []
            child_mute_params = self._random_mutate(parent_mute_params)
            self.prev_used_params.append(child_mute_params)
        elif mutate == 'none':
            child_mute_params = parent_mute_params
        else: raise Exception('no valid mutation chosen')
        full_params.update(child_mute_params)
        param_vals = {key:obj["val"] for (key,obj) in full_params.items()}
        # monte carlo runs are exponentially related to success rate. Increasing the exponent makes the curve more severe. At the TARGET_SUCCESS_RATE, you'll get the MAX_MONTE_RUNS
        override_dict = {'monte_carlo_runs' : int(max(INITIAL_MONTE_RUNS,(min(MAX_MONTE_RUNS,
                            (MAX_MONTE_RUNS * (success_rate + (1-TARGET_SUCCESS_RATE)) ** 70))))) }
        # if we're on the first child of a set, the simulator will generate returns and feed them back. For the next children, that same set of returns will be reused
        if idx != 0:
            override_dict['returns']  = self.returns
        print(f"monte runs: {override_dict['monte_carlo_runs']}")
        new_simulator = Simulator(param_vals,override_dict)
        child_success_rate, self.returns = new_simulator.main()
        child_End_Time = time.time()
        if(DEBUG_LVL>=2):
            print(f"child generation time: {round(child_End_Time-child_Start_Time,2)}")
        return (child_success_rate,child_mute_params)
    
        
    
if __name__ == '__main__':
    algorithm = Algorithm()
    algorithm.main()