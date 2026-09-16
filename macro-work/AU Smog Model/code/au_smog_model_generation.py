"""Generate the AU SMOG model using its saved historical fit.

Builds the historical AU data and state-space model, then applies the fitted
coefficients recorded in output/au_ss1_output.csv. Saves those coefficients for
au_smog_model_update.py to reuse when new observations become available.

Replicates "Model Estimation Code SMOG AU.prg":
  - data transforms from "results/AU SMOG Model Inputs.xlsx" (Generation sheet)
  - HP-filter initial state and saved historical fitted coefficients
  - 7-state / 3-signal state-space model
  - Kalman smoothed states -> output gap, y_star, u_star

States:  [gap, gap_1, gap_2, y_star, y_star_1, u_star, u_star_1]
Signals: y  = y_star + phi3*covid_d + gap + e_y
         u  = u_star + lambda3*gap + rho*(u(-1) - u_star_1) + e_u
         pi = Phillips curve (see obs_intercept) + lambda1*gap + e_pi
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

# Resolve the copied files in this repository, including in interactive cells.
try:
    HERE = Path(__file__).resolve().parent.parent
except NameError:
    REPO_ROOT = next(
        (folder for folder in (Path.cwd(), *Path.cwd().parents)
         if (folder / ".git").exists()),
        None,
    )
    if REPO_ROOT is None:
        raise RuntimeError("Open the GitHub repository before running this code as cells")
    HERE = REPO_ROOT / "macro-work" / "AU Smog Model"
    if not HERE.is_dir():
        raise FileNotFoundError(f"AU SMOG files are missing from {HERE}")
IR_DIR = HERE  # Interest Rates (this file now lives at the folder root)
INPUTS_XLSX = IR_DIR / "results" / "AU SMOG Model Inputs.xlsx"
GENERATION_SHEET = "Generation"
UPDATE_SHEET = "Update"
OUT_DIR = HERE / "output"
PARAMETERS_FILE = HERE / "au_smog_fitted_parameters.json"
REFERENCE_COEFFICIENTS_FILE = OUT_DIR / "au_ss1_output.csv"


#Estimatoin Sample we're interseted in
ESMPL_FIRST = "1980Q1"
ESMPL_LAST = "2023Q4"

# The compact workbooks have one header row and contain only these fields.
# Historical unemployment here is the corrected series, copied from the
# maintained inputs when the generation workbook was assembled.
HISTORICAL_COLUMNS = [
    "date", "real_gdp_non_farm_sa", "cpi_trimmed_spliced",
    "import_price_deflator", "covid_d", "labour2", "unemployment",
]
MODEL_INPUT_COLUMNS = [
    "date", "real_gdp_non_farm_sa", "import_price_deflator",
    "cpi_trimmed_spliced", "unemployment", "covid_d", "labour",
]


#Parameter names we use to form the models
PARAM_NAMES = [
    "beta1", "beta2", "beta3",
    "eps1", "eps2", "eps3", "eps5", "eps6", "eps7",
    "g_star", "gamma", "lambda1", "lambda3",
    "phi1", "phi2", "phi3", "psi", "rho",
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
    df = df.set_index("date").loc[:ESMPL_LAST].astype(float)

    return df
#%%
#Do the hp trend - eahc functions is just a section  - this is for initial values
def hp_trend(series, lamb=1000.0, end=ESMPL_LAST, boost=0):
    """HP trend on the available data through `end`.

    boost > 0 applies the Phillips-Shi boosted HP filter (cycle re-filtered
    `boost` extra times) - the EViews code uses hpf(lambda=1000, m=2, ic).
    """
    # Only use data up to the estimation end date, and drop missing quarters.
    # Slicing here prevents the filter from "seeing" later data, which would
    # otherwise leak future information into the starting values.
    x = series.loc[:end].dropna()

    # The Hodrick-Prescott filter splits a series into a smooth TREND and a
    # cyclical REMAINDER. lamb controls smoothness: higher = smoother trend.
    # (1600 is the usual quarterly default; 1000 here follows the EViews code.)
    cycle, trend = sm.tsa.filters.hpfilter(x, lamb=lamb)

    # "Boosting" (Phillips-Shi): the plain HP filter leaves some genuine trend
    # behind in the cycle, especially at the end of the sample where it has no
    # future data to lean on. Re-filtering the cycle extracts that leftover
    # trend and hands it back, reducing the well-known end-point bias.
    for _ in range(boost):
        cycle2, _ = sm.tsa.filters.hpfilter(cycle, lamb=lamb)  # trend still hiding in the cycle
        cycle = cycle2                                          # what remains is the purer cycle
        trend = x - cycle                                       # so the trend absorbs the rest

    # Put the result back on the FULL index: quarters after `end` (or dropped
    # as missing) come back as NaN rather than silently disappearing.
    return trend.reindex(series.index)
#%%%
#Build the dataset as we have it to store all in d
def build_dataset(boost=1):
    """Full-sample transforms exactly as in the EViews programme."""

    #Get the raw dataset we had before
    raw = load_data()
    d = pd.DataFrame(index=raw.index)

    #Biulding the raw dataset
    d["gdp"] = np.log(raw["real_gdp_non_farm_sa"])
    cpi = raw["cpi_trimmed_spliced"]
    d["inflation"] = pcy(cpi)
    d["expectations"] = d["inflation"].rolling(4).mean()          # @movav(.,4)
    d["delta_nulc"] = pcy(raw["labour2"])
    d["delta_4_pm"] = raw["import_price_deflator"] - raw["import_price_deflator"].shift(4)
    d["unemployment"] = raw["unemployment"]
    d["covid_d"] = raw["covid_d"]

    # HP-filter initial values (EViews: hpf(lambda=1000, m=2, ic))
    #These are for the unobserved stasrting values
    d["ham_u_star"] = hp_trend(d["unemployment"], boost=boost)
    d["ham_y_star"] = hp_trend(d["gdp"], boost=boost)
    d["ham_g_star"] = 100.0 * (d["ham_y_star"] / d["ham_y_star"].shift(1) - 1.0)
    d["ham_gap"] = d["gdp"] - d["ham_y_star"]

    # inflation-targeting dummy: 0 through 1993Q1, 1 after
    d["d_it"] = (d.index > pd.Period("1993Q1", freq="Q")).astype(float)

    #These are the observed endogenous variables
    d["y"] = d["gdp"]
    d["pi"] = d["inflation"]
    d["pi_e"] = d["expectations"]
    d["u"] = d["unemployment"]
    return d
#%%
#This is about building the estimation frame, so the actual dataframes we use for estimatoin
def build_estimation_frames(d, first=ESMPL_FIRST, last=ESMPL_LAST):
    """Endog + exogenous regressors on the estimation window.

    """

    #pd.period converts it into quarterly object
    #Slice returns the two endpoints
    sl = slice(pd.Period(first, freq="Q"), pd.Period(last, freq="Q"))

    #seelct on thigns between those endpoints AND endpoints
    w = d.loc[sl]

    #Dummy for philips curve (in write as D^{IT})
    nd = 1.0 - w["d_it"]

    #ex - builsd exogenous data frame
    ex = pd.DataFrame(index=w.index)
    ex["covid_d"] = w["covid_d"]
    ex["u1"] = w["u"].shift(1)
    ex["pie_d"] = w["pi_e"] * w["d_it"]
    ex["pie_nd"] = w["pi_e"] * nd
    ex["pi1"] = w["pi"].shift(1)
    ex["pi2"] = w["pi"].shift(2)
    # (1-D_it) at time t multiplies the lagged values (as in the EViews signal eq).
    # Where D_it = 1 these terms are exactly zero, even if the lag is missing.
    ex["pi3_nd"] = np.where(nd == 0.0, 0.0, w["pi"].shift(3) * nd)
    ex["nulc1_nd"] = np.where(nd == 0.0, 0.0, w["delta_nulc"].shift(1) * nd)
    ex["pm1"] = w["delta_4_pm"].shift(1)
    ex["d_it"] = w["d_it"]

    #Build endogenous data frame
    endog = w[["y", "u", "pi"]].copy()
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
class SmogAU(MLEModel):
    """7-state / 3-signal SMOG state-space model (AU)."""

    # NOTE: the EViews programme *looks* like it sets the prior variance to 0.8
    # via a chained assignment, but EViews evaluates that as comparisons - the
    # model actually ran with a ZERO prior covariance and mprior as the t=1
    # state. Verified: P=0 + "direct" reproduces EViews' loglike to 4dp and the
    # smoothed paths to ~5e-4 (rounding of the published coefficients).

    #Function 1
    #Role is to set the object up
    #Store data and build matrices
    #
    def __init__(self, endog, exog, svec, prior_var=0.0, init_mode="direct"):

        #Store inputs on object that we will want to examien in the objectc
        #Storing all the settings
        #Store exogenous variables
        self.exog_df = exog

        #Store starting values
        self.svec = np.asarray(svec, dtype=float)

        #Store starting value prior variances
        self.prior_var = float(prior_var)
        #Store string about how the filter starts direct or propergate
        self.init_mode = init_mode  # "direct": a1|0 = svec; "propagate": a1|0 = T svec + c

        #Copy endogenous variables
        endog = endog.copy()
        # A signal is unusable when its exogenous regressors are missing
        # (EViews "partial observations").

        #T/F about where missing values are
        miss_y = exog["covid_d"].isna()
        #T/F about missing values
        miss_u = exog["u1"].isna()

        #Set inflation columns
        pi_cols = ["pie_d", "pie_nd", "pi1", "pi2", "pi3_nd", "nulc1_nd", "pm1"]
        #Are any of them missing for each row
        miss_pi = exog[pi_cols].isna().any(axis=1)

        #Put missing values as NAN
        endog.loc[miss_y, "y"] = np.nan
        endog.loc[miss_u, "u"] = np.nan
        endog.loc[miss_pi, "pi"] = np.nan

        #Validation check
        self.n_partial = int(((miss_y | miss_u | miss_pi) & endog.notna().any(axis=1)).sum())


        #Fill na's
        self.ex = exog.fillna(0.0).to_numpy().T  # (k_exog, nobs)
        self.ex_cols = list(exog.columns)

        #No idea what this did
        super().__init__(endog, k_states=7, k_posdef=3,
                         initialization="known", constant=self.svec,
                         stationary_cov=self.prior_var * np.eye(7))

        # fixed structure - from equations of variables
        #Z matix in measuremetn equatoin
        Z = np.zeros((3, 7))
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

        self["obs_intercept"] = np.zeros((3, self.nobs))
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
        self["design", 1, 6] = -p["rho"]
        self["design", 2, 0] = p["lambda1"]

        self["transition", 0, 0] = p["phi1"]
        self["transition", 0, 1] = p["phi2"]
        self["state_intercept", 3, 0] = p["g_star"]

        self["obs_cov"] = np.diag([p["eps1"] ** 2, p["eps2"] ** 2, p["eps3"] ** 2])
        self["state_cov"] = np.diag([p["eps5"] ** 2, p["eps6"] ** 2, p["eps7"] ** 2])

        # Keep complex-step derivatives during optimisation instead of
        # discarding their imaginary perturbations.
        d_obs = np.zeros((3, self.nobs), dtype=np.result_type(params, float))
        d_obs[0] = p["phi3"] * self._col("covid_d")
        d_obs[1] = p["rho"] * self._col("u1")
        nd = 1.0 - self._col("d_it")
        d_obs[2] = ((1 - p["beta1"] - p["beta2"]) * self._col("pie_d")
                    + (1 - p["beta1"] - p["beta2"] - p["beta3"] - p["gamma"]) * self._col("pie_nd")
                    + p["beta1"] * self._col("pi1")
                    + p["beta2"] * self._col("pi2")
                    + p["beta3"] * self._col("pi3_nd")
                    + p["gamma"] * self._col("nulc1_nd")
                    + p["psi"] * self._col("pm1"))
        self["obs_intercept"] = d_obs

        # prior on the initial state
        P0 = self.prior_var * np.eye(7)
        if self.init_mode == "direct":
            a1, P1 = self.svec, P0
        else:  # propagate through the transition once
            T = self["transition"]
            c = np.ravel(self["state_intercept"])
            RQR = self["selection"] @ self["state_cov"] @ self["selection"].T
            a1 = T @ self.svec + c
            P1 = T @ P0 @ T.T + RQR
        self.ssm.initialize_known(a1, P1)
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
def save_results(out, out_dir=OUT_DIR, name="smog_au"):
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
        **{f"beta{i}": f"BETA({i})" for i in (1, 2, 3)},
        **{f"eps{i}": f"EPSILON({i})" for i in (1, 2, 3, 5, 6, 7)},
        "g_star": "G_STAR(1)", "gamma": "GAMMA(1)",
        "lambda1": "LAMBDA(1)", "lambda3": "LAMBDA(3)",
        "phi1": "PHI(1)", "phi2": "PHI(2)", "phi3": "PHI(3)",
        "psi": "PSI(1)", "rho": "RHO(1)",
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
        "model": "AU SMOG",
        "sample_first": ESMPL_FIRST,
        "sample_last": ESMPL_LAST,
        "parameter_names": PARAM_NAMES,
        "parameters": [float(value) for value in params],
        "initial_state": [float(value) for value in svec],
        "log_likelihood": float(log_likelihood),
        "source": "fitted coefficients in output/au_ss1_output.csv",
    }
    temporary = PARAMETERS_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(PARAMETERS_FILE)
    print(f"Fixed parameters: {PARAMETERS_FILE}")


def main():
    OUT_DIR.mkdir(exist_ok=True)

    #Build data set
    d = build_dataset(boost=1)

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
    mod = SmogAU(endog, exog, svec)


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
