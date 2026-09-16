# Run the three country models, then rebuild their five saved charts.
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
for country, script in [("Australia", "au.py"), ("Japan", "jp.py"), ("Korea", "kr.py")]:
    folder = ROOT / country
    subprocess.run([sys.executable, script], cwd=folder, check=True)
subprocess.run([sys.executable, "make_charts.py"], cwd=ROOT, check=True)
