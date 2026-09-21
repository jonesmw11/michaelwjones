# Extend KR SMOG to new quarters while holding fitted parameters fixed.
#
# Update the Update sheet of code/KR SMOG Model Inputs.xlsx, then run this script. It retains
# the original 2000Q1–2022Q4 estimation data and smooths the extended series
# with the coefficients saved by kr_smog_model_generation.py. It does not fit a
# new parameter vector.

# %% Imports and file paths
# Load dependencies and locate KR SMOG inputs and outputs.
import sys
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

# Keep the import and paths usable when running cells without __file__.
try:
    CODE_DIR = Path(__file__).resolve().parent
except NameError:
    CODE_DIR = next(
        (candidate for parent in (Path.cwd(), *Path.cwd().parents)
         for candidate in (
             parent / "code",
             parent / "macro-work" / "KR" / "SMOG Model" / "code",
             parent / "michaelwjones" / "macro-work" / "KR" / "SMOG Model" / "code",
         ) if (candidate / "kr_smog_model_generation.py").is_file()),
        None,
    )
    if CODE_DIR is None:
        raise FileNotFoundError("Open the KR SMOG Model repository folder before running cells")
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
import kr_smog_model_generation as model_code
import kr_smog_figure_generation as figure_code

HERE = CODE_DIR.parent
PARAMETERS_FILE = HERE / "kr_smog_fitted_parameters.json"
RESULTS_FILE = HERE / "results" / "smog_kr_python.csv"
FILTERED_RESULTS_FILE = HERE / "results" / "smog_kr_filtered_states.csv"

# %% Saved parameters
# Read and validate the coefficients and initial state fitted by the generator.
def load_fixed_parameters():
    # Require saved fit.
    if not PARAMETERS_FILE.is_file():
        raise FileNotFoundError(
            f"Missing {PARAMETERS_FILE}. Run kr_smog_model_generation.py once first."
        )
    # Read fitted coefficients.
    payload = json.loads(PARAMETERS_FILE.read_text(encoding="utf-8"))
    if (payload.get("parameter_names") != model_code.PARAM_NAMES
            or payload.get("sample_first") != model_code.ESMPL_FIRST
            or payload.get("sample_last") != model_code.ESMPL_LAST):
        raise ValueError("Saved parameters do not match this KR SMOG specification")
    # Validate parameter shapes.
    params = np.asarray(payload["parameters"], dtype=float)
    initial_state = np.asarray(payload["initial_state"], dtype=float)
    if (params.shape != (len(model_code.PARAM_NAMES),)
            or initial_state.shape != (7,)
            or not np.isfinite(params).all()
            or not np.isfinite(initial_state).all()):
        raise ValueError("Saved parameters or initial state are invalid")
    return params, initial_state


# %% Latest observations
# Read and transform new quarterly inputs from the update worksheet.
def load_latest_inputs():
    # Read latest worksheet.
    raw = pd.read_excel(
        model_code.INPUTS_XLSX, sheet_name=model_code.UPDATE_SHEET,
        usecols=model_code.MODEL_INPUT_COLUMNS,
    )
    raw = raw.loc[raw["date"].notna()].copy()
    raw["date"] = pd.PeriodIndex(pd.to_datetime(raw["date"]), freq="Q")
    # Order quarterly observations.
    raw = raw.set_index("date").sort_index()
    raw = raw.loc[~raw.index.duplicated(keep="first")]
    numeric = [
        "real_gdp_sa", "labour_sa", "cpi_core_sa",
        "unemployment", "expectations_bok", "import_price_deflator",
    ]
    raw[numeric] = raw[numeric].apply(pd.to_numeric, errors="coerce")
    # Build model signals.
    d = pd.DataFrame(index=raw.index)
    d["y"] = np.log(raw["real_gdp_sa"])
    d["pi"] = model_code.pcy(raw["cpi_core_sa"])
    d["pi_e"] = raw["expectations_bok"]
    d["delta_nulc"] = model_code.pcy(raw["labour_sa"])
    d["delta_4_pm"] = raw["import_price_deflator"] - raw["import_price_deflator"].shift(4)
    d["u"] = raw["unemployment"]
    return d


# %% Update workflow
# Extend the sample, smooth and filter states, and save the latest results.
def main(check_only=False):
    # Reuse fixed parameters.
    params, initial_state = load_fixed_parameters()
    historical = model_code.build_dataset().loc[:model_code.ESMPL_LAST]
    latest_data = load_latest_inputs()
    first_new = pd.Period(model_code.ESMPL_LAST, freq="Q") + 1
    required = ["y", "u", "pi", "pi_e", "delta_nulc", "delta_4_pm"]
    # Find latest complete quarter.
    complete = latest_data.loc[first_new:, required].dropna()
    if complete.empty:
        raise ValueError("No complete KR quarter after the original estimation sample")
    latest = complete.index.max()
    newer = latest_data.loc[first_new:latest]
    expected = pd.period_range(first_new, latest, freq="Q")
    if not newer.index.equals(expected) or newer[required].isna().any().any():
        raise ValueError("The new quarterly KR inputs have a gap or missing model values")
    # Append new observations.
    combined = pd.concat([historical, newer]).sort_index()
    endog, exog = model_code.build_estimation_frames(
        combined, last=str(latest)
    )
    # Smooth extended sample.
    fitted = model_code.SmogKR(endog, exog, initial_state).smooth(
        params, cov_type="none"
    )
    out = model_code.smoothed_states(fitted, endog.index).rename(
        columns={"gap_smooth_final": "output_gap"}
    )[["output_gap", "y_star", "u_star"]]
    # Extract real-time estimates.
    filtered = pd.DataFrame(
        fitted.filtered_state[[0, 3, 5]].T,
        index=endog.index,
        columns=["output_gap", "y_star", "u_star"],
    )
    filtered["output_gap"] *= 100.0  # log deviation -> per cent of potential
    if (not np.isfinite(out.to_numpy()).all()
            or not np.isfinite(filtered.to_numpy()).all()):
        raise ValueError("Updated state estimates contain missing or infinite values")
    print(f"KR SMOG: {len(out)} quarters through {latest}; fixed parameters unchanged")
    # Write updated results.
    if not check_only:
        RESULTS_FILE.parent.mkdir(exist_ok=True)
        temporary = RESULTS_FILE.with_suffix(".csv.tmp")
        out.to_csv(temporary, index_label="date")
        temporary.replace(RESULTS_FILE)
        print(f"Saved {RESULTS_FILE}")
        temporary = FILTERED_RESULTS_FILE.with_suffix(".csv.tmp")
        filtered.to_csv(temporary, index_label="date")
        temporary.replace(FILTERED_RESULTS_FILE)
        print(f"Saved {FILTERED_RESULTS_FILE}")
        figure_code.save_figures(out, combined["u"], "smoothed")
        figure_code.save_figures(filtered, combined["u"], "filtered")
    return out


# %% Script entry point
# Parse command-line options and run the model update.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extend KR SMOG using fixed fitted parameters"
    )
    parser.add_argument("--check-only", action="store_true",
                        help="calculate updated states without writing the result CSV")
    args = parser.parse_args()
    main(check_only=args.check_only)
