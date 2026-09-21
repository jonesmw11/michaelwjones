# Run the three VAR inflation models, then rebuild their five saved charts.
# %% Imports and project location
# Resolve the country folders and use the current Python interpreter.
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
# %% Country model runs
# Re-estimate the Australian, Japanese, and Korean VAR forecasts.
models = [
    (("AU", "Inflation Model"), "au.py"),
    (("JP", "Inflation Model"), "jp.py"),
    (("KR", "Inflation Model"), "kr.py"),
]
for folder_parts, script in models:
    folder = ROOT.joinpath(*folder_parts)
    subprocess.run([sys.executable, script], cwd=folder, check=True)
# %% Chart generation
# Refresh the five charts after all forecast CSVs are saved.
charts = ROOT.parent / "Charts"
subprocess.run([sys.executable, "make_charts.py"], cwd=charts, check=True)
subprocess.run([sys.executable, "build_model_summary.py"], cwd=charts, check=True)
subprocess.run([sys.executable, "build_results_dashboard.py"], cwd=charts, check=True)
