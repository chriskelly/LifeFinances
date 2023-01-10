# LifeFInances

## Dependencies
Supported for python version >= 3.9.

The code requires various packages, which are listed in `requirements.text`. To install them all at once, run the following command in the top-level directory of this repository
```bash
pip install -r requirements.txt
```
## First Time Usage
- After installing dependencies, run `python app.py`. The GUI should show up in your browser. It's still a work in progress, but you can navigate to Simulator, then click run, and after a few moments, you should see a chart pop up with hundreds of lines. These are all the individual results of a simulation based on the default parameters. You'll also see the success rate. The success rate represents what percentage of the time you did not run out of money before the final year (default: 2090).

<img src="https://user-images.githubusercontent.com/3745832/206873001-fc1954ce-5610-46f1-955e-b158f7c96d2c.png" width="200">

- Next you'll want to put in your own parameters to see how you would perform! While some parameters can be adjusted on the Parameter page, this is also still a work in progress (a big heap of data validation needed). As of now, you can't add future jobs, add more/remove kids, or add more/remove historic earnings. For now, to test out the application fully, the database (`/data/data.db`) needs to be modified directly using a viewer like [DB Browser](https://sqlitebrowser.org/)
  - Under job_incomes, consider each item in the array to be a different "job". Jobs are considered sequential: the last date of the first job is assumed to be the start date of the second job.  A gap can be represented as a "job" with 0 income.
  - Earnings Record is used for calculating social security. If you put your historical earnings here, your social security calculations will be more accurate.
  - As of now, California state taxes are used by default. Will expand support for selecting different states in the future, but in the meantime, you'd need to adjust the single/married brackets and standard deductions in `data/constants.py` to use other state rates.
- Now you can rerun the simulation to see the results of your parameters.
- After you've played around with the parameters and simulator results, you can then head over to the optimization algorithm. Because there are so many combinations of parameters, it's tiring to try out all of them to see which one works best for your situation. Should you take your social security early? What if you use a bond tent, but aren't sure the right glide path? `genetic.py` is designed to iterate through different parameters in search of an optimal combination that gives a higher success rate. When it finds one that hits the success threshold (95%), it'll overwrite your database with the successful parameters. After that, it'll try again, but with a closer retirement date. You can leave it running, and it'll continue looking for better combinations. At any point, you can kill the process and you'll have the best combination saved in your database. For now, if you run the optimizer from the browser, there is no feedback in the browser. You'll see the print statements in the Terminal window that will show you progress of the algorithm. Make sure to stop the optimizer or else it will continue to run.

## Upcoming Features
- Full parameter adjustability in the GUI
- Dynamic feedback on the Optimization page while algorithm is running

## Code Structure
- `app.py`: Work-in-progress Flask application that provides GUI interaction with the other modules.
- `simulator.py`: Running this provides a success rate for the parameters set through the controller.py or directly in data/params.json. Increasing the constant MONTE_CARLO_RUNS will increase accuracy, but also increase run-time.
- `genetic.py`: Running this starts an infinite loop. The simulator will be run over and over again with slightly randomized parameters ('Range' property of any variable in data/params.json). When a parameter set is found that meets the TARGET_SUCCESS_RATE, data/params.json will be overwritten with those params, and the loop will start over again with a more aggressive FI Date target.
- data folder
  - data.db: Database with all user parameter values
  - default_values: if anything happens to your `data.db`, you can grab this copy to use
  - historical_data: project to generate returns modeled heavily after old returns. Not implemented yet
  - constants.py: constants used across multiple modules
  - param_details.json: holds details of parameter such as type and range of options
  - param_success.json: records a tally for each successful set of parameters found in genetic.py. Helps understand what parts of a attempted parameter Range are used
- diagnostics folder
  - saved folder: For every run of simulator.py, the run with the fastest failure is saved as diagnostics/saved/worst_failure.csv. When simulator.py is run with the constant DEBUG_LVL >= 2, you can save the results of individual runs. They'll be in this folder as well
  - Diagnostics.ipynb: A general notebook used for looking at individual runs and doing sanity checks
- models folder
  - annuity.py: Annuity Class object. Used in simulator.py if Life Cycle Annuity Allocation Method is selected 
  - model.py: GUI model module
  - returnGenerator.py: Generates randomized returns for equity and real estate. Also generates random inflation data
  - skewDist.py: used by returnGenerator to skew distributions of inflation to match historical data better
  - socialSecuity.py: Calculates social security payments in simulator.py
- templates folder: view templates for Flask
  
  
