# Bulldozer

Input your arcgis user name and password so bulldozer can create a csv of the logs ordered by frequency.

It will then clean the logs for the next run.

## Installation

1. Clone or download the repository
1. Create a conda environment 
   - `conda create --clone arcgispro-py3 --name bulldozer`
1. Activate the environment and install the dependencies
   - `activate bulldozer`
   - `python -m pip install -U pip`
   - `pip install -r path\to\requirements.txt`
1. Replace `servers.sample.py` with `servers.py` and fill in server tokens
1. Create a `.bat` file to schedule bulldozer
   - `call activate bulldozer`
   - `python path\to\bulldozer.py ship app --clean --email`
1. Use the task scheduler to call the bat file on a schedule
