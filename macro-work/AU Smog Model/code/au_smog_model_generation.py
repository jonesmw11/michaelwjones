# Fit the AU SMOG state-space model on historical Australian data.
#
# Builds model inputs from the Generation sheet of AU SMOG Model Inputs.xlsx,
# estimates coefficients by Python maximum likelihood, and saves those
# coefficients and the initial state for fixed-parameter updates.
#
# States:  [gap, gap_1, gap_2, y_star, y_star_1, u_star, u_star_1]
# Signals: y  = y_star + phi3*covid_d + gap + e_y
# u  = u_star + lambda3*gap + rho*(u(-1) - u_star_1) + e_u
# pi = Phillips curve (see obs_intercept) + lambda1*gap + e_pi
# %% Imports and file paths
# Load the modelling libraries and locate inputs and outputs in this repository.
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize
from statsmodels.tsa.statespace.mlemodel import MLEModel

# Resolve the copied files in this repository, including in interactive cells.
try:
    HERE = Path(__file__).resolve().parent.parent
except NameError:
    HERE = next(
        (candidate for parent in (Path.cwd(), *Path.cwd().parents)
         for candidate in (
             parent,
             parent / "macro-work" / "AU Smog Model",
             parent / "michaelwjones" / "macro-work" / "AU Smog Model",
         ) if (candidate / "code" / "AU SMOG Model Inputs.xlsx").is_file()),
        None,
    )
    if HERE is None:
        raise FileNotFoundError("Open the repository before running AU SMOG cells")
IR_DIR = HERE  # Interest Rates (this file now lives at the folder root)
INPUTS_XLSX = IR_DIR / "code" / "AU SMOG Model Inputs.xlsx"
GENERATION_SHEET = "Generation"
UPDATE_SHEET = "Update"
OUT_DIR = HERE / "output"
PARAMETERS_FILE = HERE / "au_smog_fitted_parameters.json"
FIT_HISTORY_FILE = OUT_DIR / "au_smog_fit_history.csv"
FIT_CONTRIBUTIONS_FILE = OUT_DIR / "au_smog_fit_likelihood_by_quarter.csv"


# %% Model configuration
# Define the estimation sample, workbook columns, and coefficient order.
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


PARAM_NAMES = [
    "beta1", "beta2", "beta3",
    "eps1", "eps2", "eps3", "eps5", "eps6", "eps7",
    "g_star", "gamma", "lambda1", "lambda3",
    "phi1", "phi2", "phi3", "psi", "rho",
]
# %% Annual percentage change
# Convert a quarterly series into its four-quarter percentage change.
def pcy(x):
    return 100.0 * (x / x.shift(4) - 1.0)

# %% Historical data loading
# Read the generation worksheet and index its observations by quarter.
def load_data():
    df = pd.read_excel(INPUTS_XLSX, sheet_name=GENERATION_SHEET,
                       usecols=HISTORICAL_COLUMNS)
    df["date"] = pd.PeriodIndex(pd.to_datetime(df["date"]), freq="Q")
    df = df.set_index("date").loc[:ESMPL_LAST].astype(float)

    return df
# %% Historical trend estimate
# Apply the HP filter to obtain starting estimates of unobserved trends.
def hp_trend(series, lamb=1000.0, end=ESMPL_LAST, boost=0):
    # Estimate starting HP trend.
    # Exclude future observations.
    x = series.loc[:end].dropna()

    # Separate trend and cycle.
    cycle, trend = sm.tsa.filters.hpfilter(x, lamb=lamb)

    # Reduce endpoint bias.
    for _ in range(boost):
        cycle2, _ = sm.tsa.filters.hpfilter(cycle, lamb=lamb)  # trend still hiding in the cycle
        cycle = cycle2                                          # what remains is the purer cycle
        trend = x - cycle                                       # so the trend absorbs the rest

    # Preserve quarterly alignment.
    return trend.reindex(series.index)
# %% Model dataset
# Transform the raw series and create observed signals and trend-based inputs.
def build_dataset(boost=1):
    # Build historical model inputs.

    # Read historical series.
    raw = load_data()
    d = pd.DataFrame(index=raw.index)

    # Transform observed variables.
    d["gdp"] = np.log(raw["real_gdp_non_farm_sa"])
    cpi = raw["cpi_trimmed_spliced"]
    d["inflation"] = pcy(cpi)
    d["expectations"] = d["inflation"].rolling(4).mean()          # @movav(.,4)
    d["delta_nulc"] = pcy(raw["labour2"])
    d["delta_4_pm"] = raw["import_price_deflator"] - raw["import_price_deflator"].shift(4)
    d["unemployment"] = raw["unemployment"]
    d["covid_d"] = raw["covid_d"]

    # Seed latent trends.
    d["ham_u_star"] = hp_trend(d["unemployment"], boost=boost)
    d["ham_y_star"] = hp_trend(d["gdp"], boost=boost)
    d["ham_g_star"] = 100.0 * (d["ham_y_star"] / d["ham_y_star"].shift(1) - 1.0)
    d["ham_gap"] = d["gdp"] - d["ham_y_star"]

    # Mark targeting regime.
    d["d_it"] = (d.index > pd.Period("1993Q1", freq="Q")).astype(float)

    # Name observed signals.
    d["y"] = d["gdp"]
    d["pi"] = d["inflation"]
    d["pi_e"] = d["expectations"]
    d["u"] = d["unemployment"]
    return d
# %% Estimation frames
# Assemble the observed series and regressors over the estimation window.
def build_estimation_frames(d, first=ESMPL_FIRST, last=ESMPL_LAST):
    # Select estimation observations.

    # Select quarterly endpoints.
    sl = slice(pd.Period(first, freq="Q"), pd.Period(last, freq="Q"))

    w = d.loc[sl]

    # Separate policy regimes.
    nd = 1.0 - w["d_it"]

    # Build lagged regressors.
    ex = pd.DataFrame(index=w.index)
    ex["covid_d"] = w["covid_d"]
    ex["u1"] = w["u"].shift(1)
    ex["pie_d"] = w["pi_e"] * w["d_it"]
    ex["pie_nd"] = w["pi_e"] * nd
    ex["pi1"] = w["pi"].shift(1)
    ex["pi2"] = w["pi"].shift(2)
    # Mask inactive regime lags.
    ex["pi3_nd"] = np.where(nd == 0.0, 0.0, w["pi"].shift(3) * nd)
    ex["nulc1_nd"] = np.where(nd == 0.0, 0.0, w["delta_nulc"].shift(1) * nd)
    ex["pm1"] = w["delta_4_pm"].shift(1)
    ex["d_it"] = w["d_it"]

    # Select measured signals.
    endog = w[["y", "u", "pi"]].copy()
    return endog, ex
# %% Initial state vector
# Set the seven starting states from the historical trend estimates.
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
# Define the AU SMOG observation, transition, and variance equations.
class SmogAU(MLEModel):
    # Define AU model equations.

    # Start from HP estimates.

    # Initialize Kalman system.
    def __init__(self, endog, exog, svec, prior_var=0.0, init_mode="direct"):

        # Keep model inputs.
        self.exog_df = exog

        # Seed latent states.
        self.svec = np.asarray(svec, dtype=float)

        # Set prior uncertainty.
        self.prior_var = float(prior_var)
        # Choose initialization mode.
        self.init_mode = init_mode

        # Protect source observations.
        endog = endog.copy()
        # Mask incomplete signals.

        miss_y = exog["covid_d"].isna()
        miss_u = exog["u1"].isna()

        # Check Phillips regressors.
        pi_cols = ["pie_d", "pie_nd", "pi1", "pi2", "pi3_nd", "nulc1_nd", "pm1"]
        miss_pi = exog[pi_cols].isna().any(axis=1)

        endog.loc[miss_y, "y"] = np.nan
        endog.loc[miss_u, "u"] = np.nan
        endog.loc[miss_pi, "pi"] = np.nan

        # Count partial quarters.
        self.n_partial = int(((miss_y | miss_u | miss_pi) & endog.notna().any(axis=1)).sum())


        # Fill masked regressors.
        self.ex = exog.fillna(0.0).to_numpy().T  # (k_exog, nobs)
        self.ex_cols = list(exog.columns)

        # Initialize Kalman model.
        super().__init__(endog, k_states=7, k_posdef=3,
                         initialization="known", constant=self.svec,
                         stationary_cov=self.prior_var * np.eye(7))

        # Map states to signals.
        Z = np.zeros((3, 7))
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

        self["obs_intercept"] = np.zeros((3, self.nobs))
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
        self["design", 1, 6] = -p["rho"]
        self["design", 2, 0] = p["lambda1"]

        self["transition", 0, 0] = p["phi1"]
        self["transition", 0, 1] = p["phi2"]
        self["state_intercept", 3, 0] = p["g_star"]

        # Set signal noise.
        self["obs_cov"] = np.diag([p["eps1"] ** 2, p["eps2"] ** 2, p["eps3"] ** 2])
        self["state_cov"] = np.diag([p["eps5"] ** 2, p["eps6"] ** 2, p["eps7"] ** 2])

        # Preserve derivative precision.
        # Build signal intercepts.
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

        # Initialize state uncertainty.
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

# %% Smoothed state extraction
# Label the fitted latent states and express the output gap in percent.
def smoothed_states(res, index):
    # Extract smoothed model states.
    out = pd.DataFrame(res.smoothed_state.T, index=index,
                       columns=["gap", "gap_1", "gap_2", "y_star", "y_star_1",
                                "u_star", "u_star_1"])
    out["gap_smooth_final"] = out["gap"] * 100.0
    return out

# %% Historical result export
# Write the reported smoothed states to a CSV file.
def save_results(out, out_dir=OUT_DIR, name="smog_au"):
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
    unemployment_gap = w["u"] - w["ham_u_star"]

    # Fit starting regressions.
    def regression(columns):
        frame = pd.concat(columns, axis=1).dropna()
        y = frame.iloc[:, 0].to_numpy()
        x = frame.iloc[:, 1:].to_numpy()
        coefficients = np.linalg.lstsq(x, y, rcond=None)[0]
        return coefficients, float(np.std(y - x @ coefficients))

    (phi1, phi2), gap_noise = regression([gap, gap.shift(1), gap.shift(2)])
    (rho, lambda3), unemployment_noise = regression(
        [unemployment_gap, unemployment_gap.shift(1), gap]
    )
    post = w.loc["1993Q2":]
    (beta1, beta2, lambda1, psi), inflation_noise = regression([
        post["pi"] - post["pi_e"],
        post["pi"].shift(1) - post["pi_e"],
        post["pi"].shift(2) - post["pi_e"],
        post["ham_gap"], post["delta_4_pm"].shift(1),
    ])
    # Assemble coefficient guesses.
    start = np.array([
        beta1, beta2, -0.5,
        max(w["gdp"].diff().std() / 2, 0.001),
        max(unemployment_noise, 0.01),
        max(inflation_noise, 0.05),
        max(gap_noise, 0.001),
        max(w["ham_y_star"].diff().std(), 0.001),
        max(w["ham_u_star"].diff().std(), 0.01),
        w["gdp"].diff().median(), 0.005,
        lambda1, lambda3, phi1, phi2, 0.0, psi, rho,
    ], dtype=float)
    # Reject invalid guesses.
    if start.shape != (len(PARAM_NAMES),) or not np.isfinite(start).all():
        raise ValueError("Could not derive finite optimizer starting values")
    return start
# %% Maximum-likelihood estimation
# Optimize the bounded likelihood and check that the fit converged.
def fit_parameters(mod, d):
    # Fit bounded model likelihood.
    # Prevent NAIRU collapse.
    unemployment_change_sd = float(
        d["u"].loc[ESMPL_FIRST:ESMPL_LAST].diff().std()
    )
    nairu_noise_floor = unemployment_change_sd / 2
    if not np.isfinite(nairu_noise_floor) or nairu_noise_floor <= 0:
        raise ValueError("Cannot derive the NAIRU innovation floor from the data")
    # Balance optimizer coordinates.
    scale = np.array([1, 1, 1, .01, .1, .3, .01, .005, .1,
                      .01, .01, 5, 20, 1, 1, .01, .02, 1])
    # Set parameter bounds.
    lower = np.array([-3, -3, -3, .00001, .00001, .00001,
                      .00001, .00001, nairu_noise_floor, -.02, -2, -100,
                      -100, -1.8, -1, -1, -1, -.99])
    upper = np.array([3, 3, 3, .5, 2, 5, .1, .1, 2, .03,
                      2, 100, -.01, 1.8, 1, 1, 1, .99])
    # Clip feasible starting point.
    start = np.clip(initial_parameters(d), lower + 1e-8, upper - 1e-8)
    # Track optimizer path.
    history = []
    contributions = []

    def record_iteration(scaled):
        # Track accepted optimizer steps.
        params = np.asarray(scaled) * scale
        # Measure each quarter.
        quarterly = np.asarray(mod.loglikeobs(params), dtype=float)
        if quarterly.shape != (mod.nobs,) or not np.isfinite(quarterly).all():
            raise RuntimeError("Cannot record a finite AU likelihood trajectory")
        iteration = len(history)
        # Store accepted parameters.
        history.append({"iteration": iteration,
                        "log_likelihood": float(quarterly.sum()),
                        **dict(zip(PARAM_NAMES, params.astype(float)))})
        contributions.append(quarterly.copy())

    def negative_log_likelihood(scaled):
        try:
            value = -float(mod.loglike(scaled * scale))
        except (ValueError, np.linalg.LinAlgError):
            return 1e12
        return value if np.isfinite(value) else 1e12

    # Record initial likelihood.
    record_iteration(start / scale)
    # Maximize Kalman likelihood.
    result = minimize(
        negative_log_likelihood, start / scale, method="L-BFGS-B",
        bounds=list(zip(lower / scale, upper / scale)),
        callback=record_iteration,
        options={"maxiter": 700, "maxfun": 16000, "ftol": 1e-10},
    )
    # Reject failed fit.
    if not result.success or not np.isfinite(result.fun):
        raise RuntimeError(
            f"Python maximum-likelihood fit did not converge: {result.message}"
        )
    params = result.x * scale
    if not np.allclose(params, np.array([history[-1][name] for name in PARAM_NAMES]),
                       rtol=0, atol=1e-12):
        record_iteration(result.x)
    if not np.isclose(history[-1]["log_likelihood"], -result.fun, atol=1e-6):
        raise RuntimeError("Recorded AU likelihood differs from the optimizer result")
    print(f"Python fit converged in {result.nit} iterations; "
          f"log likelihood {-result.fun:.6f}")
    return params, result, nairu_noise_floor, history, contributions


# %% Optimizer diagnostics
# Save accepted likelihood values and quarterly contributions.
def save_fit_history(history, contributions, index):
    # Save optimizer progress.
    # Summarize accepted steps.
    trajectory = pd.DataFrame(history)
    trajectory["change_in_log_likelihood"] = trajectory["log_likelihood"].diff()
    columns = ["iteration", "log_likelihood", "change_in_log_likelihood", *PARAM_NAMES]
    trajectory = trajectory[columns]
    # Expand quarterly contributions.
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


# %% Fit convergence figures
# Show parameter paths and likelihood gains across accepted optimizer steps.
def show_fit_figures(history, nairu_noise_floor):
    # Check recorded values.
    trajectory = pd.DataFrame(history)
    columns = ["iteration", "log_likelihood", *PARAM_NAMES]
    if trajectory.empty or not set(columns).issubset(trajectory.columns):
        raise ValueError("AU fit history is empty or missing parameters")
    values = trajectory[columns].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("AU fit history contains non-finite values")
    iterations = trajectory["iteration"].to_numpy(dtype=int)
    likelihood = trajectory["log_likelihood"].to_numpy(dtype=float)
    if not np.array_equal(iterations, np.arange(len(iterations))):
        raise ValueError("AU fit iterations must start at zero and be consecutive")
    # Compare every coefficient.
    parameter_fig, axes = plt.subplots(6, 3, figsize=(15, 18), sharex=True,
                                      layout="constrained")
    for ax, name in zip(axes.flat, PARAM_NAMES):
        series = trajectory[name].to_numpy(dtype=float)
        ax.plot(iterations, series, color="#0B6E4F", linewidth=1.8)
        ax.axhline(series[-1], color="#7A7A7A", linestyle="--", linewidth=1)
        if name == "eps7":
            ax.axhline(nairu_noise_floor, color="#BD6745", linestyle=":",
                       linewidth=1.5)
        ax.set_title(f"{name}  |  final {series[-1]:.4g}", loc="left", fontsize=11)
        ax.grid(axis="y", color="#E9E9E9")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
        ax.margins(y=0.12)
    for ax in axes[-1]:
        ax.set_xlabel("Accepted iteration")
    parameter_fig.suptitle("AU SMOG parameter convergence\n"
                           "Dashed: final value    Dotted on eps7: NAIRU noise floor",
                           fontsize=15)

    # Show total fit improvement.
    likelihood_fig, (ax_total, ax_gain) = plt.subplots(
        2, 1, figsize=(11, 8), sharex=True, layout="constrained"
    )
    ax_total.plot(iterations, likelihood, color="#0B6E4F", linewidth=2)
    ax_total.scatter([iterations[0], iterations[-1]],
                     [likelihood[0], likelihood[-1]], color="#0B6E4F", s=30)
    ax_total.set_ylabel("Total log likelihood")
    ax_total.set_title("AU SMOG likelihood convergence", loc="left", fontsize=16)

    # Expose late small gains.
    gains = np.diff(likelihood)
    ax_gain.plot(iterations[1:], gains, color="#3D8F73", linewidth=1.7)
    if len(gains) and np.all(gains > 0):
        ax_gain.set_yscale("log")
        ax_gain.set_ylabel("Gain per iteration (log scale)")
    else:
        ax_gain.set_ylabel("Gain per iteration")
        ax_gain.axhline(0, color="#7A7A7A", linewidth=1)
    ax_gain.set_xlabel("Accepted iteration")
    for ax in (ax_total, ax_gain):
        ax.grid(axis="y", color="#E9E9E9")
        ax.spines[["top", "right"]].set_visible(False)
    # Display both figures.
    plt.show()
    plt.close(parameter_fig)
    plt.close(likelihood_fig)


# %% Fitted parameter export
# Save coefficients and initial states for later fixed-parameter updates.
def save_parameters(params, svec, log_likelihood, iterations,
                    nairu_noise_floor):
    # Save fitted model parameters.
    # Record reproducible fit.
    payload = {
        "model": "AU SMOG",
        "sample_first": ESMPL_FIRST,
        "sample_last": ESMPL_LAST,
        "parameter_names": PARAM_NAMES,
        "parameters": [float(value) for value in params],
        "initial_state": [float(value) for value in svec],
        "log_likelihood": float(log_likelihood),
        "source": "Python maximum likelihood (L-BFGS-B)",
        "converged": True,
        "iterations": int(iterations),
        "nairu_innovation_sd_floor": float(nairu_noise_floor),
    }
    # Replace file atomically.
    temporary = PARAMETERS_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(PARAMETERS_FILE)
    print(f"Fixed parameters: {PARAMETERS_FILE}")


# %% Generation workflow
# Prepare data, estimate the model, smooth states, and save its outputs.
def main():
    OUT_DIR.mkdir(exist_ok=True)

    # Prepare historical inputs.
    d = build_dataset(boost=1)

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
    mod = SmogAU(endog, exog, svec)


    # Fit model coefficients.
    params, fit_result, nairu_noise_floor, history, contributions = fit_parameters(mod, d)
    # Smooth fitted states.
    res = mod.smooth(params, cov_type="none")

    # Label smoothed states.
    out = smoothed_states(res, endog.index)

    # Persist fitted outputs.
    save_parameters(params, svec, res.llf, fit_result.nit,
                    nairu_noise_floor)
    save_fit_history(history, contributions, endog.index)
    save_results(out)
    # Show estimation progress.
    show_fit_figures(history, nairu_noise_floor)

    return out
# %% Script entry point
# Run the complete generation workflow when this file is executed directly.
if __name__ == "__main__":
    main()
