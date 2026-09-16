"""Generate the KR SMOG model using its saved historical fit.

Builds the historical KR data and state-space model, then applies the fitted
coefficients recorded in output/kr_ss1_output.csv. Saves those coefficients for
kr_smog_model_update.py to reuse when new observations become available.

Replicates the fitted KR SMOG specification:
  - data transforms from "results/KR SMOG Model Inputs.xlsx" (Generation sheet)
  - HP-filter initial state and saved historical fitted coefficients
  - 7-state / 4-signal state-space model
  - Kalman smoothed states -> output gap, y_star, u_star

States:  [gap, gap_1, gap_2, y_star, y_star_1, u_star, u_star_1]
Signals: y  = y_star + gap + e_y
         u  = u_star + lambda3*gap + rho1*(u(-1) - u_star_1) + e_u
         pi = Phillips curve (see obs_intercept) + lambda1*gap + e_pi
         delta_nulc = wage curve + lambda2*(u(-1) - u_star_1) + e_nulc
"""
#%%
#Buidl Librariers
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.statespace.mlemodel import MLEModel

# Resolve the bundled files in this folder, including in interactive cells.
try:
    HERE = Path(__file__).resolve().parent.parent
except NameError:
    HERE = next((folder for folder in (Path.cwd(), *Path.cwd().parents)
                 if (folder / "results" / "KR SMOG Model Inputs.xlsx").is_file()), None)
    if HERE is None:
        raise RuntimeError("Open the KR SMOG Model folder before running code as cells")
IR_DIR = HERE  # this model uses files in its own folder
INPUTS_XLSX = IR_DIR / "results" / "KR SMOG Model Inputs.xlsx"
GENERATION_SHEET = "Generation"
UPDATE_SHEET = "Update"
OUT_DIR = HERE / "output"
PARAMETERS_FILE = HERE / "kr_smog_fitted_parameters.json"
REFERENCE_COEFFICIENTS_FILE = OUT_DIR / "kr_ss1_output.csv"


#Estimatoin Sample we're interseted in
ESMPL_FIRST = "2000Q1"
ESMPL_LAST = "2022Q4"

# The compact workbooks have one header row and contain only these fields.
# Historical transforms and HP prior columns are bundled from the KR
# estimation export so the original fitted sample can be reproduced exactly.
HISTORICAL_COLUMNS = [
    "date", "y", "u", "pi", "pi_e", "delta_nulc", "delta_4_pm",
    "ham_gap", "ham_y_star", "ham_u_star",
]
MODEL_INPUT_COLUMNS = [
    "date", "real_gdp_sa", "labour_sa", "cpi_core_sa",
    "unemployment", "expectations_bok", "import_price_deflator",
]


#Parameter names we use to form the models
PARAM_NAMES = [
    "beta1", "beta2", "beta4",
    "eps1", "eps2", "eps3", "eps4", "eps5", "eps6", "eps7",
    "g_star", "lambda1", "lambda2", "lambda3",
    "phi1", "phi2", "psi", "rho1",
]
#%%
# # ---------------------------------------------------------------- data

#Create a function that performs percentage change
def pcy(x):
    return 100.0 * (x / x.shift(4) - 1.0)

#This loads the data - doesnt necessarily need to be in a functoin
def load_data():
    df = pd.read_excel(INPUTS_XLSX, sheet_name=GENERATION_SHEET,
                       usecols=HISTORICAL_COLUMNS)
    df["date"] = pd.PeriodIndex(pd.to_datetime(df["date"]), freq="Q")
    # The red rows in the workbook are reference data, not estimation inputs.
    df = df.set_index("date").loc[ESMPL_FIRST:ESMPL_LAST].astype(float)
    return df
#%%
#Do the hp trend - eahc functions is just a section  - this is for initial values
#The exact HP starting values used in the fitted KR sample are bundled in the
#Generation tab. This avoids recomputing them from a later data vintage.

#%%%
#Build the dataset as we have it to store all in d
def build_dataset():
    """Historical KR model variables and HP starting values."""
    return load_data()
#%%
#This is about building the estimation frame, so the actual dataframes we use for estimatoin
def build_estimation_frames(d, first=ESMPL_FIRST, last=ESMPL_LAST):
    """Four observables and their lagged regressors on the selected window."""
    sl = slice(pd.Period(first, freq="Q"), pd.Period(last, freq="Q"))
    w = d.loc[sl]
    ex = pd.DataFrame(index=w.index)
    ex["u1"] = w["u"].shift(1)
    ex["pie"] = w["pi_e"]
    ex["pi1"] = w["pi"].shift(1)
    ex["pi2"] = w["pi"].shift(2)
    ex["pm1"] = w["delta_4_pm"].shift(1)
    endog = w[["y", "u", "pi", "delta_nulc"]].copy()
    return endog, ex
#%%
#Make the starting values apparent
def make_svec(d, first=ESMPL_FIRST):
    p0 = pd.Period(first, freq="Q")
    g = d["ham_gap"]
    ys = d["ham_y_star"]
    us = d["ham_u_star"]
    return np.array([
        g[p0 + 2], g[p0 + 1], g[p0],
        ys[p0 + 1], ys[p0],
        us[p0 + 1], us[p0],
    ])
#%%
# ---------------------------------------------------------------- model
#Import from Statsmodel MLE  - create an object from it  - so thsis i
#is creating the model like LM does in R , lm()
#CREATING THE MODEL
class SmogKR(MLEModel):
    """7-state / 4-signal SMOG state-space model (KR)."""

    # NOTE: the fitted programme used a zero prior covariance and its
    # supplied prior mean as the state at t=1. The gap shock variance is
    # scaled by 1/100 in this KR specification.

    #Function 1
    #Role is to set the object up
    #Store data and build matrices
    #
    def __init__(self, endog, exog, svec, prior_var=0.0):
        #Store inputs on object that we will want to examien in the objectc
        self.exog_df = exog
        self.svec = np.asarray(svec, dtype=float)
        self.prior_var = float(prior_var)

        #Copy endogenous variables
        endog = endog.copy()
        # A signal is unusable when its exogenous regressors are missing.
        miss_u = exog["u1"].isna()
        miss_pi = exog[["pie", "pi1", "pi2", "pm1"]].isna().any(axis=1)
        miss_nulc = exog[["pie", "pi1", "u1"]].isna().any(axis=1)
        endog.loc[miss_u, "u"] = np.nan
        endog.loc[miss_pi, "pi"] = np.nan
        endog.loc[miss_nulc, "delta_nulc"] = np.nan
        self.n_partial = int(((miss_u | miss_pi | miss_nulc)
                              & endog.notna().any(axis=1)).sum())

        #Fill na's
        self.ex = exog.fillna(0.0).to_numpy().T
        self.ex_cols = list(exog.columns)
        super().__init__(endog, k_states=7, k_posdef=3,
                         initialization="known", constant=self.svec,
                         stationary_cov=self.prior_var * np.eye(7))

        # fixed structure - from equations of variables
        #Z matix in measuremetn equatoin
        Z = np.zeros((4, 7))
        Z[0, 0] = 1.0   # y: gap
        Z[0, 3] = 1.0   # y: y_star
        Z[1, 5] = 1.0   # u: u_star
        self["design"] = Z

        #T Matrix in transition qeuation
        T = np.zeros((7, 7))
        T[1, 0] = 1.0   # gap_1 = gap(-1)
        T[2, 1] = 1.0   # gap_2 = gap_1(-1)
        T[3, 3] = 1.0   # y_star random walk + drift
        T[4, 3] = 1.0   # y_star_1 = y_star(-1)
        T[5, 5] = 1.0   # u_star random walk
        T[6, 5] = 1.0   # u_star_1 = u_star(-1)
        self["transition"] = T

        #R matrix in transitoin qeuation that refelcts covariance structure
        R = np.zeros((7, 3))
        R[0, 0] = 1.0   # e_gap
        R[3, 1] = 1.0   # e_y_star
        R[5, 2] = 1.0   # e_u_star
        self["selection"] = R
        self["obs_intercept"] = np.zeros((4, self.nobs))
        self["state_intercept"] = np.zeros((7, 1))

    #Need to chekc tehse functoins
    @property
    def param_names(self):
        return PARAM_NAMES

    @property
    def start_params(self):
        raise NotImplementedError("pass start_params explicitly")

    def _col(self, name):
        return self.ex[self.ex_cols.index(name)]

    #Builds new matrices from candiatet vector
    def update(self, params, **kwargs):
        params = super().update(params, **kwargs)
        p = dict(zip(PARAM_NAMES, params))

        #Design matrices
        self["design", 1, 0] = p["lambda3"]
        self["design", 1, 6] = -p["rho1"]
        self["design", 2, 0] = p["lambda1"]
        self["design", 3, 6] = -p["lambda2"]

        self["transition", 0, 0] = p["phi1"]
        self["transition", 0, 1] = p["phi2"]
        self["state_intercept", 3, 0] = p["g_star"]

        self["obs_cov"] = np.diag([p[f"eps{i}"] ** 2 for i in (1, 2, 3, 4)])
        self["state_cov"] = np.diag([p["eps5"] ** 2 * 0.01,
                                     p["eps6"] ** 2, p["eps7"] ** 2])

        # Keep complex-step derivatives during optimisation instead of
        # discarding their imaginary perturbations.
        d_obs = np.zeros((4, self.nobs), dtype=np.result_type(params, float))
        d_obs[1] = p["rho1"] * self._col("u1")
        d_obs[2] = ((1 - p["beta1"] - p["beta2"]) * self._col("pie")
                    + p["beta1"] * self._col("pi1")
                    + p["beta2"] * self._col("pi2")
                    + p["psi"] * self._col("pm1"))
        d_obs[3] = ((1 - p["beta4"]) * self._col("pie")
                    + p["beta4"] * self._col("pi1")
                    + p["lambda2"] * self._col("u1"))
        self["obs_intercept"] = d_obs

        # prior on the initial state
        self.ssm.initialize_known(self.svec, self.prior_var * np.eye(7))
        return params

#%%
# ---------------------------------------------------------------- output

def smoothed_states(res, index):
    """Pull the Kalman-smoothed states out of a fitted model.

    res   : the results object returned by the Kalman smoother
    index : the quarterly index to label the rows with

    Returns a DataFrame of all seven states plus the output gap expressed
    in per cent (the gap is in log units, so x100 makes it a percentage
    deviation from potential).
    """
    out = pd.DataFrame(res.smoothed_state.T, index=index,
                       columns=["gap", "gap_1", "gap_2", "y_star", "y_star_1",
                                "u_star", "u_star_1"])
    out["gap_smooth_final"] = out["gap"] * 100.0
    return out

#sSave results, we can use this later
def save_results(out, out_dir=OUT_DIR, name="smog_kr"):
    """Write the historical smoothed states to CSV.

    out     : the frame returned by smoothed_states()
    out_dir : folder to write into
    name    : filename stem, so other countries can reuse this
    """
    out_dir.mkdir(exist_ok=True)

    #Only the three reported series go to the CSV
    csv_path = out_dir / f"{name}_smoothed_states.csv"
    out[["gap_smooth_final", "y_star", "u_star"]].to_csv(csv_path)
    print(f"Smoothed states: {csv_path}")

#%%
def load_reference_parameters():
    """Read the final fitted coefficients from the bundled EViews table."""
    labels = {
        **{f"beta{i}": f"BETA({i})" for i in (1, 2, 4)},
        **{f"eps{i}": f"EPSILON({i})" for i in (1, 2, 3, 4, 5, 6, 7)},
        "g_star": "G_STAR(1)",
        "lambda1": "LAMBDA(1)", "lambda2": "LAMBDA(2)",
        "lambda3": "LAMBDA(3)",
        "phi1": "PHI(1)", "phi2": "PHI(2)",
        "psi": "PSI(1)", "rho1": "RHO(1)",
    }
    found = {}
    with REFERENCE_COEFFICIENTS_FILE.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].strip() in labels.values():
                found[row[0].strip()] = float(row[1])
    missing = [name for name in PARAM_NAMES if labels[name] not in found]
    if missing:
        raise ValueError(f"Reference coefficient table is missing {missing}")
    params = np.array([found[labels[name]] for name in PARAM_NAMES])
    if not np.isfinite(params).all():
        raise ValueError("Reference coefficients must be finite")
    return params


def save_parameters(params, svec, log_likelihood):
    """Persist coefficients and initial state for fixed-parameter updates."""
    payload = {
        "model": "KR SMOG",
        "sample_first": ESMPL_FIRST,
        "sample_last": ESMPL_LAST,
        "parameter_names": PARAM_NAMES,
        "parameters": [float(value) for value in params],
        "initial_state": [float(value) for value in svec],
        "log_likelihood": float(log_likelihood),
        "source": "fitted coefficients in output/kr_ss1_output.csv",
    }
    temporary = PARAMETERS_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(PARAMETERS_FILE)
    print(f"Fixed parameters: {PARAMETERS_FILE}")


def main():
    OUT_DIR.mkdir(exist_ok=True)

    #Build data set
    d = build_dataset()

    #Serpate out teh frames
    endog, exog = build_estimation_frames(d)

    #Cehck samples
    print(f"Estimation sample: {endog.index[0]} - {endog.index[-1]}  ({len(endog)} obs)")

    #Get starting values for the unobserved states
    svec = make_svec(d)

    print("\nsvec (prior mean of the initial state):")
    for n, a in zip(["gap(3)", "gap(2)", "gap(1)", "y*(2)", "y*(1)", "u*(2)", "u*(1)"],
                    svec):
        print(f"  {n:8s} {a:12.6f}")

    #Lets hold data and fixed matriaces in mod
    mod = SmogKR(endog, exog, svec)


    # Reuse the historical model estimates; new observations will not
    # change these coefficients.
    params = load_reference_parameters()
    res = mod.smooth(params, cov_type="none")

    #Pull the smoothed states out of the fitted model
    out = smoothed_states(res, endog.index)

    save_parameters(params, svec, res.llf)
    save_results(out)

    return out
#%%
if __name__ == "__main__":
    main()

# %%
