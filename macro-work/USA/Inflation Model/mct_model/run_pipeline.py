# Default entry point: the complete estimator runs in Python.
#
# MCT PIPELINE MAP
# [1] Source data -> prepare_inputs.py -> data/*.mat
# [2] Python entry -> run_pipeline.py -> run_python.py
# [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
# [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
# [5] Optional validation/reference tooling -> Archive/
# Archived Octave route and downloaded research material are not used in production.
#
# THIS FILE: STAGE 2, DEFAULT PIPELINE ENTRY.
# It is a thin, user-facing alias that transfers execution to run_python.py.

# %% Imports
# Load the standard-library helpers used to locate and execute the Python driver.
import runpy
from pathlib import Path

# %% Forward command-line execution to run_python.py
# Execute run_python.py as __main__. Existing command-line arguments remain
# available, so this wrapper accepts the same vintage and MCMC settings.
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('run_python.py')),run_name='__main__')
