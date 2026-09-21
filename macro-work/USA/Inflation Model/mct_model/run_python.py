# Package-backed MCT estimation, with no MATLAB or Octave subprocess.
#
# MCT PIPELINE MAP
# [1] Source data -> prepare_inputs.py -> data/*.mat
# [2] Python entry -> run_pipeline.py -> run_python.py
# [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
# [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
# [5] Optional validation/reference tooling -> Archive/
# Archived Octave route and downloaded research material are not used in production.
#
# THIS FILE: STAGE 2, PYTHON ESTIMATION DRIVER.
# It loads prepared inputs, runs the MCT engine, saves draws, and starts reporting.

# %% Numerical runtime configuration
# Limit BLAS/OpenMP to one thread before importing numerical libraries; this avoids
# excessive threading overhead for the relatively small matrices used repeatedly.
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')

# %% Imports and project path
# Load command-line, provenance, MAT-file, model-engine, and reporting utilities.
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import numpy as np
import scipy
from scipy.io import loadmat, savemat
import statsmodels
from mct_python import MCT
from export_results import export

ROOT = Path(__file__).resolve().parent


# %% Run one complete Python estimation
# Load one prepared vintage, initialize the MCT object, run burn-in and posterior
# sampling, save the raw MAT result, export reports, and maintain a status record.
def run(vintage, draws=3000, burn=3000, thin=2, seed=2022):
    if draws < 2 or burn < 0 or thin < 1:
        raise ValueError('Need draws >= 2, burn >= 0, thin >= 1')
    data = loadmat(ROOT/'data'/f'{vintage}.mat',simplify_cells=True)
    np.testing.assert_allclose(data['weights'].sum(axis=1),1,atol=1e-12)
    destination = ROOT/'results/python'
    destination.mkdir(exist_ok=True,parents=True)
    tag = f'{vintage}_d{draws}_b{burn}_t{thin}_s{seed}'
    status_path = destination/f'{tag}_status.json'
    state = {'pid':os.getpid(),'status':'running','vintage':vintage,'seed':seed,
             'engine':'Python / statsmodels simulation smoother / NumPy-SciPy sampling',
             'started_utc':datetime.now(timezone.utc).isoformat(),
             'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'statsmodels':statsmodels.__version__}}

    def progress(iteration,total,elapsed):
        state.update(iteration=iteration,total=total,elapsed_seconds=elapsed)
        status_path.write_text(json.dumps(state,indent=2))
        print(f'{vintage}: {iteration}/{total}; {elapsed:.1f}s; projected remaining {elapsed*(total-iteration)/iteration/3600:.2f}h',flush=True)

    try:
        print(f'START Python {vintage}: draws={draws} burn={burn} thin={thin}',flush=True)
        model = MCT(data['y'],seed=seed)
        result = model.sample(data['weights'],draws,burn,thin,progress)
        result.update(month_codes=data['month_codes'],settings={'n_draw':draws,'n_burn':burn,'n_thin':thin},seed=seed,prior=asdict(model.priors),engine=state['engine'])
        path = destination/f'{tag}.mat'
        savemat(path,result,do_compression=True)
        export(path)
        state.update(status='complete',finished_utc=datetime.now(timezone.utc).isoformat(),result=str(path))
    except Exception as exc:
        state.update(status='failed',error=str(exc))
        raise
    finally:
        status_path.write_text(json.dumps(state,indent=2))


# %% Command-line entry point
# Parse the requested vintage and sampling settings, then run one or both prepared
# datasets sequentially through the complete Python estimation workflow.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vintage',choices=['replication_202310','current_reconstruction','both'],default='both')
    parser.add_argument('--draws',type=int,default=3000)
    parser.add_argument('--burn',type=int,default=3000)
    parser.add_argument('--thin',type=int,default=2)
    parser.add_argument('--seed',type=int,default=2022)
    args = parser.parse_args()
    vintages = ['replication_202310','current_reconstruction'] if args.vintage=='both' else [args.vintage]
    for vintage in vintages:
        run(vintage,args.draws,args.burn,args.thin,args.seed)
