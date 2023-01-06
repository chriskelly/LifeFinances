# LifeFInances

## Dependencies
Supported for python version >= 3.9.

The code requires various packages, which are listed in `dependencies.text`. To install them all at once, run the following command in the top-level directory of this repository
```bash
pip install -r requirements.txt
```
## First Time Usage
- After installing dependencies, run `python simulator.py`. After a few moments, you should see a chart pop up with hundreds of lines. These are all the individual results of a simulation based on the default parameters. After closing the chart, you'll see the success rate and median final net worth in the terminal window. The success rate represents what percentage of the time you did not run out of money before the final year (default: 2090) without running out of money.

<img src="https://user-images.githubusercontent.com/3745832/206873001-fc1954ce-5610-46f1-955e-b158f7c96d2c.png" width="200"> ![image](https://user-images.githubusercontent.com/3745832/206873090-318451cd-df8d-4a51-b625-a100ad0c9e6f.png)

- Next you'll want to put in your own parameters to see how you would perform! After running the simulator the first time, you'll be able to edit the parameters in `data/params.json`. In the future, this will be in a cleaner GUI. Within each dictionary, you can modify the value in "val": "value" pairs to match your own situation. For anything that's a text input, you can select from the options in "range". 
  - Under incomes, consider each item in the array to be a different "job". Jobs are considered sequential: the last date of the first job is assumed to be the start date of the second job.  A gap can be represented as a "job" with 0 income.
  - Earnings Record is used for calculating social security. If you put your historical earnings here, your social security calculations will be more accurate.
  - As of now, California state taxes are used by default. Will expand support for selecting different states in the future, but in the meantime, you'd need to adjust the single/married brackets and standard deductions in `data/constants.py` to use other state rates.
- Now you can rerun `simulator.py` to see the results of your simulation.
- After you've played around with the parameters and simulator results, you can then head over to the optimization algorithm. Because there are so many combinations of parameters, it's tiring to try out all of them to see which one works best for your situation. Should you take your social security early? What if you use a bond tent, but aren't sure the right glide path? `genetic.py` is designed to iterate through different parameters in search of an optimal combination that gives a higher success rate. When it finds one that hits the success threshold (95%), it'll overwrite your `params.json` with the successful parameters. After that, it'll try again, but with a closer retirement date. You can leave it running, and it'll continue looking for better combinations. At any point, you can kill the process and you'll have the best combination saved in your `params.json` file.

## Upcoming Features
- Web based GUI for adjusting parameters and seeing results!

## Code Structure
- `simulator.py`: Running this provides a success rate for the parameters set through the controller.py or directly in data/params.json. Increasing the constant MONTE_CARLO_RUNS will increase accuracy, but also increase run-time.
- `genetic.py`: Running this starts an infinite loop. The simulator will be run over and over again with slightly randomized parameters ('Range' property of any variable in data/params.json). When a parameter set is found that meets the TARGET_SUCCESS_RATE, data/params.json will be overwritten with those params, and the loop will start over again with a more aggressive FI Date target.
- `controller.py`: the controller of an MVC GUI that allows you to modify the parameters used in other modules. Needs to be updated, so advise to directly edit data/params.json instead
- data folder
  - default_params: if anything happens to your params.json, you can grab this copy to use
  - historical_data: project to generate returns modeled heavily after old returns. Not implemented yet
  - constants.py: constants used across multiple modules
  - params.json: main file for holding user parameters
  - param_success.json: records a tally for each successful set of parameters found in genetic.py. Helps understand what parts of a attempted parameter Range are used
  - ss_earnings.csv: Used to calculate social security payments in simulator.py. Needs to be moved into params.json somehow in the future
- diagnostics folder
  - saved folder: For every run of simulator.py, the run with the fastest failure is saved as diagnostics/saved/worst_failure.csv. When simulator.py is run with the constant DEBUG_LVL >= 2, you can save the results of individual runs. They'll be in this folder as well
  - Diagnostics.ipynb: A general notebook used for looking at individual runs and doing sanity checks
- models folder
  - annuity.py: Annuity Class object. Used in simulator.py if Life Cycle Annuity Allocation Method is selected 
  - model.py: GUI model module
  - returnGenerator.py: Generates randomized returns for equity and real estate. Also generates random inflation data
  - skewDist.py: used by returnGenerator to skew distributions of inflation to match historical data better
  - socialSecuity.py: Calculates social security payments in simulator.py
- views folder: view modules for the GUI
  
  
