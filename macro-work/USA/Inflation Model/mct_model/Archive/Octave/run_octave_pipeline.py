# Run both full estimations sequentially, with persistent logs and result exports.
#
# MCT PIPELINE MAP
# [1] Source data -> prepare_inputs.py -> data/*.mat
# [2] Python entry -> run_pipeline.py -> run_python.py
# [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
# [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
# [5] Validation -> validate_python.py
# Optional Octave reference:
# prepare_runtime.py -> run_octave_pipeline.py -> run_mct.m -> export_results.py
#
# THIS FILE: OPTIONAL OCTAVE STAGE B, REFERENCE PIPELINE DRIVER.
# It prepares inputs/runtime, launches the preserved estimator in Octave, and
# sends completed reference-run outputs through the shared exporter.

# %% Imports and command-line settings
# Load subprocess, status, file, and reporting utilities; require the caller to
# provide an Octave executable and select which prepared vintage to run.
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from export_results import export

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--octave', type=Path, required=True)
parser.add_argument('--vintage', choices=['replication_202310', 'current_reconstruction', 'both'], default='both')
args = parser.parse_args()

# %% Initialize working folders, environment, and status
# Run from the model folder, limit numerical-library threads, and create a durable
# status structure that survives long reference runs.
os.chdir(ROOT)
results = ROOT / 'results'
results.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
state = {'pid': os.getpid(), 'started_utc': datetime.now(timezone.utc).isoformat(), 'completed': []}


# %% Persist Octave pipeline status
# Save the current stage, vintage, completion list, or failure information as JSON.
def save_state():
    (results / 'pipeline_status.json').write_text(json.dumps(state, indent=2))


# %% Prepare and run the Octave reference workflow
# Rebuild inputs and the headless adapter, estimate each selected vintage through
# run_mct.m, capture logs, export results, and record completion or failure.
try:
    for script in ['prepare_inputs.py', 'prepare_runtime.py']:
        subprocess.run([sys.executable, script], check=True, env=env)
    vintages = ['replication_202310', 'current_reconstruction'] if args.vintage == 'both' else [args.vintage]
    for vintage in vintages:
        state.update(status='running', current_vintage=vintage)
        save_state()
        with (results / f'{vintage}_full.log').open('w') as log:
            subprocess.run([str(args.octave), '--quiet', '--eval', f"run_mct('{vintage}',3000,3000,2,2022);"], stdout=log, stderr=subprocess.STDOUT, env=env, check=True)
        export(results / f'{vintage}_d3000_b3000_t2_s2022.mat')
        state['completed'].append(vintage)
        save_state()
    state.update(status='complete', finished_utc=datetime.now(timezone.utc).isoformat())
except Exception as exc:
    state.update(status='failed', error=str(exc))
    raise
finally:
    save_state()
