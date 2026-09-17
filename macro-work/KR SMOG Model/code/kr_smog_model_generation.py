# Estimate and generate the KR SMOG model from its historical inputs.
#
# Builds the historical KR data and state-space model, then fits its
# coefficients by maximum likelihood in Python. Saves those coefficients for
# kr_smog_model_update.py to reuse when new observations become available.
#
# Replicates the fitted KR SMOG specification:
# - data transforms from "code/KR SMOG Model Inputs.xlsx" (Generation sheet)
# - historical HP initial state and Python-fitted coefficients
# - 7-state / 4-signal state-space model
# - Kalman smoothed states -> output gap, y_star, u_star
#
# States:  [gap, gap_1, gap_2, y_star, y_star_1, u_star, u_star_1]
# Signals: y  = y_star + gap + e_y
# u  = u_star + lambda3*gap + rho1*(u(-1) - u_star_1) + e_u
# pi = Phillips curve (see obs_intercept) + lambda1*gap + e_pi
# delta_nulc = wage curve + lambda2*(u(-1) - u_star_1) + e_nulc
# %% Imports and file paths
# Load modelling libraries and locate KR SMOG inputs and outputs.
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize
from statsmodels.tsa.statespace.mlemodel import MLEModel

# Resolve the bundled files in this folder, including in interactive cells.
try:
    HERE = Path(__file__).resolve().parent.parent
except NameError:
    HERE = next(
        (candidate for parent in (Path.cwd(), *Path.cwd().parents)
         for candidate in (
             parent,
             parent / "macro-work" / "KR SMOG Model",
             parent / "michaelwjones" / "macro-work" / "KR SMOG Model",
         ) if (candidate / "code" / "KR SMOG Model Inputs.xlsx").is_file()),
        None,
    )
    if HERE is None:
        raise FileNotFoundError("Open the repository before running KR SMOG cells")
IR_DIR = HERE  # this model uses files in its own folder
INPUTS_XLSX = IR_DIR / "code" / "KR SMOG Model Inputs.xlsx"
GENERATION_SHEET = "Generation"
UPDATE_SHEET = "Update"
OUT_DIR = HERE / "output"
PARAMETERS_FILE = HERE / "kr_smog_fitted_parameters.json"
FIT_HISTORY_FILE = OUT_DIR / "kr_smog_fit_history.csv"
FIT_CONTRIBUTIONS_FILE = OUT_DIR / "kr_smog_fit_likelihood_by_quarter.csv"


# %% Model configuration
# Define the estimation sample, workbook fields, and coefficient order.
ESMPL_FIRST = "2000Q1"
ESMPL_LAST = "2022Q4"

# The compact workbooks have one header row and contain only these fields.
# Historical transforms and HP prior columns are bundled with this model.
HISTORICAL_COLUMNS = [
    "date", "y", "u", "pi", "pi_e", "delta_nulc", "delta_4_pm",
    "ham_gap", "ham_y_star", "ham_u_star",
]
MODEL_INPUT_COLUMNS = [
    "date", "real_gdp_sa", "labour_sa", "cpi_core_sa",
    "unemployment", "expectations_bok", "import_price_deflator",
]


PARAM_NAMES = [
    "beta1", "beta2", "beta4",
    "eps1", "eps2", "eps3", "eps4", "eps5", "eps6", "eps7",
    "g_star", "lambda1", "lambda2", "lambda3",
    "phi1", "phi2", "psi", "rho1",
]
# %% Annual percentage change
# Convert a quarterly series into its four-quarter percentage change.
def pcy(x):
    return 100.0 * (x / x.shift(4) - 1.0)

# %% Historical data loading
# Read the generation worksheet and select the historical estimation sample.
def load_data():
    df = pd.read_excel(INPUTS_XLSX, sheet_name=GENERATION_SHEET,
                       usecols=HISTORICAL_COLUMNS)
    df["date"] = pd.PeriodIndex(pd.to_datetime(df["date"]), freq="Q")
    # Exclude reference rows.
    df = df.set_index("date").loc[ESMPL_FIRST:ESMPL_LAST].astype(float)
    return df
# %% Model dataset
# Read observed series and the historical HP starting states bundled in the workbook.
# This avoids recomputing them from a later data vintage.
def build_dataset():
    # Build historical model inputs.
    return load_data()
# %% Estimation frames
# Assemble observed signals and regressors over the estimation window.
def build_estimation_frames(d, first=ESMPL_FIRST, last=ESMPL_LAST):
    # Select estimation observations.
    sl = slice(pd.Period(first, freq="Q"), pd.Period(last, freq="Q"))
    w = d.loc[sl]
    # Build lagged regressors.
    ex = pd.DataFrame(index=w.index)
    ex["u1"] = w["u"].shift(1)
    ex["pie"] = w["pi_e"]
    ex["pi1"] = w["pi"].shift(1)
    ex["pi2"] = w["pi"].shift(2)
    ex["pm1"] = w["delta_4_pm"].shift(1)
    endog = w[["y", "u", "pi", "delta_nulc"]].copy()
    return endog, ex
# %% Initial state vector
# Set the seven starting states from the historical HP trends.
def make_svec(d, first=ESMPL_FIRST):
    # Locate starting quarter.
    p0 = pd.Period(first, freq="Q")
    g = d["ham_gap"]
    ys = d["ham_y_star"]
    us = d["ham_u_star"]
    # Order seven initial states.
    return np.array([
        g[p0 + 2], g[p0 + 1], g[p0],
        ys[p0 + 1], ys[p0],
        us[p0 + 1], us[p0],
    ])
# %% State-space model
# Define the KR SMOG observation, transition, and variance equations.
class SmogKR(MLEModel):
    # Define KR model equations.

    # Match KR prior scaling.

    # Initialize Kalman system.
    def __init__(self, endog, exog, svec, prior_var=0.0):
        # Keep model inputs.
        self.exog_df = exog
        self.svec = np.asarray(svec, dtype=float)
        self.prior_var = float(prior_var)

        # Protect source observations.
        endog = endog.copy()
        # Mask incomplete signals.
        miss_u = exog["u1"].isna()
        miss_pi = exog[["pie", "pi1", "pi2", "pm1"]].isna().any(axis=1)
        miss_nulc = exog[["pie", "pi1", "u1"]].isna().any(axis=1)
        endog.loc[miss_u, "u"] = np.nan
        endog.loc[miss_pi, "pi"] = np.nan
        endog.loc[miss_nulc, "delta_nulc"] = np.nan
        self.n_partial = int(((miss_u | miss_pi | miss_nulc)
                              & endog.notna().any(axis=1)).sum())

        # Fill masked regressors.
        self.ex = exog.fillna(0.0).to_numpy().T
        self.ex_cols = list(exog.columns)
        super().__init__(endog, k_states=7, k_posdef=3,
                         initialization="known", constant=self.svec,
                         stationary_cov=self.prior_var * np.eye(7))

        # Map states to signals.
        Z = np.zeros((4, 7))
        Z[0, 0] = 1.0   # y: gap
        Z[0, 3] = 1.0   # y: y_star
        Z[1, 5] = 1.0   # u: u_star
        self["design"] = Z

        # Advance latent states.
        T = np.zeros((7, 7))
        T[1, 0] = 1.0   # gap_1 = gap(-1)
        T[2, 1] = 1.0   # gap_2 = gap_1(-1)
        T[3, 3] = 1.0   # y_star random walk + drift
        T[4, 3] = 1.0   # y_star_1 = y_star(-1)
        T[5, 5] = 1.0   # u_star random walk
        T[6, 5] = 1.0   # u_star_1 = u_star(-1)
        self["transition"] = T

        # Route state shocks.
        R = np.zeros((7, 3))
        R[0, 0] = 1.0   # e_gap
        R[3, 1] = 1.0   # e_y_star
        R[5, 2] = 1.0   # e_u_star
        self["selection"] = R
        self["obs_intercept"] = np.zeros((4, self.nobs))
        self["state_intercept"] = np.zeros((7, 1))

    @property
    def param_names(self):
        return PARAM_NAMES

    @property
    def start_params(self):
        raise NotImplementedError("pass start_params explicitly")

    def _col(self, name):
        return self.ex[self.ex_cols.index(name)]

    # Apply trial coefficients.
    def update(self, params, **kwargs):
        # Decode candidate parameters.
        params = super().update(params, **kwargs)
        p = dict(zip(PARAM_NAMES, params))

        # Set observation loadings.
        self["design", 1, 0] = p["lambda3"]
        self["design", 1, 6] = -p["rho1"]
        self["design", 2, 0] = p["lambda1"]
        self["design", 3, 6] = -p["lambda2"]

        self["transition", 0, 0] = p["phi1"]
        self["transition", 0, 1] = p["phi2"]
        self["state_intercept", 3, 0] = p["g_star"]

        # Set signal noise.
        self["obs_cov"] = np.diag([p[f"eps{i}"] ** 2 for i in (1, 2, 3, 4)])
        self["state_cov"] = np.diag([p["eps5"] ** 2 * 0.01,
                                     p["eps6"] ** 2, p["eps7"] ** 2])

        # Preserve derivative precision.
        # Build signal intercepts.
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

        # Initialize state uncertainty.
        self.ssm.initialize_known(self.svec, self.prior_var * np.eye(7))
        return params

# %% Smoothed state extraction
# Label latent states and express the output gap in percent.
def smoothed_states(res, index):
    # Extract smoothed model states.
    out = pd.DataFrame(res.smoothed_state.T, index=index,
                       columns=["gap", "gap_1", "gap_2", "y_star", "y_star_1",
                                "u_star", "u_star_1"])
    out["gap_smooth_final"] = out["gap"] * 100.0
    return out

# %% Historical result export
# Write the reported smoothed states to a CSV file.
def save_results(out, out_dir=OUT_DIR, name="smog_kr"):
    # Save reported state estimates.
    out_dir.mkdir(exist_ok=True)

    # Export reported states.
    csv_path = out_dir / f"{name}_smoothed_states.csv"
    out[["gap_smooth_final", "y_star", "u_star"]].to_csv(csv_path)
    print(f"Smoothed states: {csv_path}")

# %% Optimizer starting values
# Estimate data-based initial guesses for the model coefficients.
def initial_parameters(d):
    # Choose data-based starting values.
    # Limit historical sample.
    w = d.loc[ESMPL_FIRST:ESMPL_LAST]
    gap = w["ham_gap"]
    ustar = w["ham_u_star"]

    # Fit starting regressions.
    def regression(columns):
        frame = pd.concat(columns, axis=1).dropna()
        y = frame.iloc[:, 0].to_numpy()
        x = frame.iloc[:, 1:].to_numpy()
        coefficients = np.linalg.lstsq(x, y, rcond=None)[0]
        return coefficients, float(np.std(y - x @ coefficients))

    (phi1, phi2), gap_noise = regression([gap, gap.shift(1), gap.shift(2)])
    (lambda3, rho1), unemployment_noise = regression([
        w["u"] - ustar, gap, w["u"].shift(1) - ustar.shift(1),
    ])
    (beta1, beta2, psi, lambda1), inflation_noise = regression([
        w["pi"] - w["pi_e"],
        w["pi"].shift(1) - w["pi_e"],
        w["pi"].shift(2) - w["pi_e"],
        w["delta_4_pm"].shift(1), gap,
    ])
    (beta4, lambda2), wage_noise = regression([
        w["delta_nulc"] - w["pi_e"],
        w["pi"].shift(1) - w["pi_e"],
        w["u"].shift(1) - ustar.shift(1),
    ])
    # Assemble coefficient guesses.
    start = np.array([
        beta1, beta2, beta4,
        max((w["y"] - w["ham_y_star"] - gap).std(), .0001),
        max(unemployment_noise, .01), max(inflation_noise, .05),
        max(wage_noise, .1), max(gap_noise * 10, .01),
        max(w["ham_y_star"].diff().std(), .001),
        max(ustar.diff().std(), .01),
        w["ham_y_star"].diff().median(),
        lambda1, lambda2, lambda3, phi1, phi2, psi, rho1,
    ], dtype=float)
    # Reject invalid guesses.
    if start.shape != (len(PARAM_NAMES),) or not np.isfinite(start).all():
        raise ValueError("Could not derive finite optimizer starting values")
    return start


# %% Maximum-likelihood estimation
# Optimize the bounded likelihood and check convergence.
def fit_parameters(mod, d):
    # Fit bounded model likelihood.
    # Balance optimizer coordinates.
    scale = np.array([1, 1, 1, .01, .1, .3, 3, .1, .005, .1,
                      .01, 5, 5, 5, 1, 1, .02, 1])
    # Set parameter bounds.
    lower = np.array([-3, -3, -3, .00001, .00001, .00001, .00001,
                      .00001, .00001, .00001, -.02, -100, -100,
                      -100, -1.8, -1, -1, -.99])
    upper = np.array([3, 3, 3, .5, 2, 5, 20, 2, .1, 2,
                      .03, 100, 100, 100, 1.8, 1, 1, .99])
    # Clip feasible starting point.
    start = np.clip(initial_parameters(d), lower + 1e-8, upper - 1e-8)
    history = []
    contributions = []

    def record_iteration(scaled):
        """Record the initial point or an accepted L-BFGS-B iteration."""
        params = np.asarray(scaled) * scale
        quarterly = np.asarray(mod.loglikeobs(params), dtype=float)
        if quarterly.shape != (mod.nobs,) or not np.isfinite(quarterly).all():
            raise RuntimeError("Cannot record a finite KR likelihood trajectory")
        iteration = len(history)
        history.append({"iteration": iteration,
                        "log_likelihood": float(quarterly.sum()),
                        **dict(zip(PARAM_NAMES, params.astype(float)))})
        contributions.append(quarterly.copy())

    def negative_log_likelihood(scaled):
        params = scaled * scale
        # Enforce stable gap dynamics.
        phi1, phi2 = params[14:16]
        if phi1 + phi2 >= .999 or phi2 - phi1 >= .999:
            return 1e10 + 1e6 * max(phi1 + phi2 - .999,
                                      phi2 - phi1 - .999, 0)
        # Evaluate Kalman likelihood.
        try:
            value = -float(mod.loglike(params))
        except (ValueError, np.linalg.LinAlgError):
            return 1e12
        # Penalize failed evaluations.
        return value if np.isfinite(value) else 1e12

    # Maximize Kalman likelihood and record each accepted step.
    record_iteration(start / scale)
    result = minimize(
        negative_log_likelihood, start / scale, method="L-BFGS-B",
        bounds=list(zip(lower / scale, upper / scale)),
        callback=record_iteration,
        options={"maxiter": 700, "maxfun": 16000, "ftol": 1e-10},
    )
    # Reject failed fit.
    if not result.success or not np.isfinite(result.fun) or result.fun >= 1e9:
        raise RuntimeError(
            f"Python maximum-likelihood fit did not converge: {result.message}"
        )
    params = result.x * scale
    if not np.allclose(params, np.array([history[-1][name] for name in PARAM_NAMES]),
                       rtol=0, atol=1e-12):
        record_iteration(result.x)
    if not np.isclose(history[-1]["log_likelihood"], -result.fun, atol=1e-6):
        raise RuntimeError("Recorded KR likelihood differs from the optimizer result")
    print(f"Python fit converged in {result.nit} iterations; "
          f"log likelihood {-result.fun:.6f}")
    return params, result, history, contributions


def save_fit_history(history, contributions, index):
    """Export accepted fits and likelihood contributions by quarter."""
    trajectory = pd.DataFrame(history)
    trajectory["change_in_log_likelihood"] = trajectory["log_likelihood"].diff()
    columns = ["iteration", "log_likelihood", "change_in_log_likelihood", *PARAM_NAMES]
    trajectory = trajectory[columns]
    quarterly = pd.DataFrame(np.vstack(contributions),
                             index=trajectory["iteration"], columns=index)
    quarterly.index.name = "iteration"
    quarterly = quarterly.stack().rename("log_likelihood_contribution").reset_index()
    quarterly.columns = ["iteration", "date", "log_likelihood_contribution"]
    quarterly["date"] = quarterly["date"].astype(str)
    for frame, path in ((trajectory, FIT_HISTORY_FILE),
                        (quarterly, FIT_CONTRIBUTIONS_FILE)):
        temporary = path.with_suffix(path.suffix + ".tmp")
        frame.to_csv(temporary, index=False)
        temporary.replace(path)
        print(f"Fit history: {path}")


# %% Fitted parameter export
# Save coefficients and initial states for later fixed-parameter updates.
def save_parameters(params, svec, log_likelihood, iterations):
    # Save fitted model parameters.
    # Record reproducible fit.
    payload = {
        "model": "KR SMOG",
        "sample_first": ESMPL_FIRST,
        "sample_last": ESMPL_LAST,
        "parameter_names": PARAM_NAMES,
        "parameters": [float(value) for value in params],
        "initial_state": [float(value) for value in svec],
        "log_likelihood": float(log_likelihood),
        "source": "Python maximum likelihood (L-BFGS-B)",
        "converged": True,
        "iterations": int(iterations),
    }
    # Replace file atomically.
    temporary = PARAMETERS_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(PARAMETERS_FILE)
    print(f"Fixed parameters: {PARAMETERS_FILE}")


# %% Generation workflow
# Prepare data, estimate the model, smooth states, and save outputs.
def main():
    OUT_DIR.mkdir(exist_ok=True)

    # Prepare historical inputs.
    d = build_dataset()

    # Split signals and regressors.
    endog, exog = build_estimation_frames(d)

    # Confirm estimation window.
    print(f"Estimation sample: {endog.index[0]} - {endog.index[-1]}  ({len(endog)} obs)")

    # Seed latent states.
    svec = make_svec(d)

    print("\nsvec (prior mean of the initial state):")
    for n, a in zip(["gap(3)", "gap(2)", "gap(1)", "y*(2)", "y*(1)", "u*(2)", "u*(1)"],
                    svec):
        print(f"  {n:8s} {a:12.6f}")

    # Build state-space model.
    mod = SmogKR(endog, exog, svec)


    # Fit model coefficients.
    params, fit_result, history, contributions = fit_parameters(mod, d)
    # Smooth fitted states.
    res = mod.smooth(params, cov_type="none")

    # Label smoothed states.
    out = smoothed_states(res, endog.index)

    # Persist fitted outputs.
    save_parameters(params, svec, res.llf, fit_result.nit)
    save_fit_history(history, contributions, endog.index)
    save_results(out)

    return out
# %% Script entry point
# Run the generation workflow when this file is executed directly.
if __name__ == "__main__":
    main()
