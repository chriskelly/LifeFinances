# LifeFInances

## Dependencies
Supported for python version >= 3.9.

The code requires various packages, which are listed in `dependencies.text`. To install them all at once, run the following command in the top-level directory of this repository
```bash
pip install -r dependencies.txt
```

## Code Structure
### Directly runnable files
- `simulator.py`: Running this provides a success rate for the parameters set through the controller.py or directly in data/params.json. Increasing the constant MONTE_CARLO_RUNS will increase accuracy, but also increase run-time.
- `genetic.py`: Running this starts an infinite loop. The simulator will be run over and over again with slightly randomized parameters ('Range' property of any variable in data/params.json). When a parameter set is found that meets the TARGET_SUCCESS_RATE, data/params.json will be overwritten with those params, and the loop will start over again with a more agressive FI Date target.
- `controller.py`: the controller of an MVC GUI that allows you to modify the parameters used in other modules. Needs to be updated, so advise to directly edit data/params.json instead

### Other files
- data folder
  - default_params: if anything happens to your params.json, you can grab this copy to use
  - historical_data: project to generate returns modeled heavily after old returns. Not implemented yet
  - constants.py: constants used across multiple modules
  - params.json: main file for holding user parameters
  - param_success.json: records a tally for each successful set of parameters found in genetic.py. Helps understand what parts of a attempted parameter Range are used
  - ss_earnings.csv: Used to calulate social security payments in simulator.py. Needs to be moved into params.json somehow in the future
- diagnostics folder
  - saved folder: For every run of simulator.py, the run with the fastest failure is saved as diagnostics/saved/worst_failure.csv. When simulator.py is run with the constant DEBUG_LVL >= 2, you can save the results of individual runs. They'll be in this folder as well
  - Diagnostics.ipynb: A general notebook used for looking at individual runs and doing sanity checks
- drawdown folder: a set of modules that aren't integrated into the code, but were made as a separate project to model drawdown of a portfolio after retirement. It would be nice to integrate it somehow in the future.
- models folder
  - annuity.py: Annuity Class object. Used in simulator.py if Life Cycle Annuity Allocation Method is selected 
  - model.py: GUI model module
  - returnGenerator.py: Generates randomized returns for equity and real estate. Also generates random inflation data
  - skewDist.py: used by returnGenerator to skew distributions of inflation to match historical data better
  - socialSecuity.py: Calculates social security payments in simulator.py
- views folder: view modules for the GUI
  
  
