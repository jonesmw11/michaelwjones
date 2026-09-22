# =============================================================================
# %% Imports and paths
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = Path(__file__).with_name("filtered_runs_finalizer_status.json")
RUNS = {
    "JP": ROOT / "macro-work/JP/Inflation Model/mct_model/results/python/japan_core_d3000_b3000_t2_s2022_status.json",
    "KR": ROOT / "macro-work/KR/Inflation Model/mct_model/results/python/korea_core_d3000_b3000_t2_s2022_status.json",
    "AU": ROOT / "macro-work/AU/Inflation Model/mct_model_core/results/python/australia_core_d3000_b3000_t2_s2022_status.json",
    "AU_HEADLINE": ROOT / "macro-work/AU/Inflation Model/mct_model_headline/results/python/australia_headline_d3000_b3000_t2_s2022_status.json",
}
FILTERED_OUTPUTS = {
    name: path.parent / "latest_filtered_labelled.csv"
    for name, path in RUNS.items()
}


# =============================================================================
# %% Status helpers
def write_status(status, **details):
    payload = {"status": status, **details}
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_runs():
    states = {}
    for name, path in RUNS.items():
        if not path.exists():
            states[name] = {"status": "missing"}
            continue
        for attempt in range(5):
            try:
                states[name] = json.loads(path.read_text(encoding="utf-8"))
                break
            except (json.JSONDecodeError, OSError):
                if attempt == 4:
                    states[name] = {"status": "transient_write"}
                else:
                    time.sleep(0.2)
    return states


# =============================================================================
# %% Wait for production completion and rebuild the dashboard
def main():
    write_status("waiting", runs=list(RUNS))
    while True:
        states = read_runs()
        failures = {
            name: state
            for name, state in states.items()
            if state.get("status") == "failed"
        }
        if failures:
            write_status("failed", failures=failures)
            return 1
        if all(state.get("status") == "complete" for state in states.values()):
            missing = [
                str(path)
                for path in FILTERED_OUTPUTS.values()
                if not path.exists()
            ]
            if missing:
                write_status("failed", error="Filtered outputs missing", missing=missing)
                return 1
            subprocess.run(
                [sys.executable, str(ROOT / "Charts/build_results_dashboard.py")],
                cwd=ROOT,
                check=True,
            )
            write_status(
                "complete",
                runs={name: state.get("result") for name, state in states.items()},
                dashboard=str(ROOT / "results_dashboard.html"),
            )
            return 0
        write_status(
            "waiting",
            progress={
                name: {
                    "status": state.get("status"),
                    "iteration": state.get("iteration"),
                    "total": state.get("total"),
                }
                for name, state in states.items()
            },
        )
        time.sleep(30)


# =============================================================================
# %% Command-line entry point
if __name__ == "__main__":
    raise SystemExit(main())
