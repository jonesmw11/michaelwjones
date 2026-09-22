# Run the self-contained Japan MCT estimator.

# =============================================================================
# %% Numerical runtime and imports
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat, savemat

from export_results import export
from mct_python import MCT

ROOT = Path(__file__).resolve().parent


# =============================================================================
# %% Estimate and export one run
def run(draws=3000, burn=3000, thin=2, seed=2022):
    data = loadmat(ROOT / "data/japan_core.mat", simplify_cells=True)
    np.testing.assert_allclose(data["weights"].sum(axis=1), 1, atol=1e-12)
    destination = ROOT / "results/python"
    destination.mkdir(exist_ok=True, parents=True)
    tag = f"japan_core_d{draws}_b{burn}_t{thin}_s{seed}"
    status_path = destination / f"{tag}_status.json"
    state = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat(), "draws": draws, "burn": burn, "thin": thin, "seed": seed}

    def progress(iteration, total, elapsed):
        state.update(iteration=iteration, total=total, elapsed_seconds=elapsed)
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"Japan MCT: {iteration}/{total}; {elapsed:.1f}s", flush=True)

    try:
        model = MCT(data["y"], seed=seed)
        result = model.sample(data["weights"], draws, burn, thin, progress)
        result.update(period_codes=data["period_codes"], settings={"n_draw": draws, "n_burn": burn, "n_thin": thin}, seed=seed, prior=asdict(model.priors))
        result_path = destination / f"{tag}.mat"
        savemat(result_path, result, do_compression=True)
        export(result_path)
        state.update(status="complete", finished_utc=datetime.now(timezone.utc).isoformat(), result=str(result_path))
    except Exception as exc:
        state.update(status="failed", error=str(exc))
        raise
    finally:
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


# =============================================================================
# %% Command-line entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=3000)
    parser.add_argument("--burn", type=int, default=3000)
    parser.add_argument("--thin", type=int, default=2)
    parser.add_argument("--seed", type=int, default=2022)
    args = parser.parse_args()
    run(args.draws, args.burn, args.thin, args.seed)
