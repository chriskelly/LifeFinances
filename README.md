# LifeFInances

## Dependencies
Supported for python version 3.10.

The code requires various packages, which are listed in the `requirements/` directory. Using virtual enviroments is recommended. To install them all at once, run the following command in the top-level directory of this repository.
```bash
pip install -r requirements/common.txt
```
or 
```bash
pip3 install -r requirements/common.txt
```
Developers should replace `common.txt` with `dev.txt`.


## First Time Usage
More documentation is still pending. In the meantime, feel free to open an issue with questions about usage.

Without Docker:
- Install the dependencies (see above)
- Look at the configs in `tests/sample_configs/` and copy the config you want to start with to the root directory under the name `config.yml`
- Review the options for allocation at [`app/data/README.md`](https://github.com/chriskelly/LifeFinances/blob/main/app/data/README.md)
- Run `flask run` from your terminal

With Docker:
- Pending...


## Code Structure
- Application entry point is `/run.py`
- While this may not stay up-to-date, you can view this [Figma board](https://www.figma.com/file/UddWSekF9Sl6REDWII9dtr/LifeFinances-Functional-Tree?type=whiteboard&node-id=0%3A1&t=p6KDxEXCU2BdB7MZ-1) to see a visual representation of the intended structure.
  
  
