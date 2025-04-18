# Mathematical Programming, Programming Project Python Framework

This framework is provided to help you get started with implementing the models for the programming project.
It uses Python 3.12 and Gurobi 12 (via `gurobipy`).

Feel free to alter the code as you see fit, but please keep existing command line arguments (like `--instance`) as they are.
You may add additional command line arguments if that is convenient for you, but please set reasonable default values.


## Project setup

1. Install `uv`: https://docs.astral.sh/uv/getting-started/installation/
2. Run `uv sync` in project root directory (i.e., where `pyproject.toml` lives) to set up the virtual environment with all dependencies.

## Running the program

1. Run `uv run src/kmst/kmst.py --help`

This will print the usage message for your program.

## Additional dependencies
You may add any additional Python dependencies you need, but please make sure to add them to the `pyproject.toml` file (e.g., with `uv add`).
Do not use `pip install`!

## Installing Gurobi

The Gurobi version included with `gurobipy` only supports models with up to 2k variables and constraints. For the larger instances, you'll need a license.

You can get a free academic named-user license to run Gurobi on your computer if you register with your TU-Wien-provided email address. See here for details: https://www.gurobi.com/features/academic-named-user-license/