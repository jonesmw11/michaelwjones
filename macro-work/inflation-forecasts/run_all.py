# Run the three country models, then rebuild their five saved charts.
# %% Imports and project location
# Resolve the country folders and use the current Python interpreter.
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
# %% Country model runs
# Re-estimate the Australian, Japanese, and Korean VAR forecasts.
for country, script in [("Australia", "au.py"), ("Japan", "jp.py"), ("Korea", "kr.py")]:
    folder = ROOT / country
    subprocess.run([sys.executable, script], cwd=folder, check=True)
# %% Chart generation
# Refresh the five charts after all forecast CSVs are saved.
subprocess.run([sys.executable, "make_charts.py"], cwd=ROOT, check=True)
