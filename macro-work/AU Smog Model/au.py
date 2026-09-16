"""Australia: SMOG output-gap model and Laubach-Williams r* model.

SMOG (quarterly, 1980Q1-2023Q4): the original RBA-style spec -
  full inflation-targeting Phillips curve (dummy switches 1993Q2), COVID
  stringency in the GDP equation, NULC equation switched off. Zero prior
  covariance (the chained smat assignment in the programme is a no-op).
  A full raw-data pipeline for FRESH estimation (transforms, boosted-HP
  initial values, OLS starting values, statsmodels MLE) is in au_pipeline.py.

LW (quarterly, 1991Q1-2023Q4): the largest LW variant - 13 states adding a
  NAIRU block (u*, Okun's law signal) to the usual y*/g*/z* chains:
    IS:       y on 2 own lags and the real-rate gap (both terms use rint(-1),
              faithful to the programme)
    Phillips: pi on the unemployment gap, expectations and output-gap lags
    Okun:     u on u* and a distributed lag of output gaps
  r* = 4*g* + z*/2.2 (the programme's reporting convention).
"""

#Import files
import numpy as np
import pandas as pd

#Import create functions from statespace.py
#Run Smog and RUN LW, actually do the modelling for us 
from statespace import run_smog, run_lw, AU13, kappa_scale

SMOG_SPEC = dict(
    sample=("1980Q1", "2023Q4"),
    u_star_lags=1, gap_ar=2, u_rho_lags=1,
    y_covid=+1.0,
    pi_type="dit_full", pi_gap_coef="lambda1", u_gap_coef="lambda3",
    nulc_type=None,
    gap_var_scale=1.0,
    prior_var=0.0,
    svec_pattern=("g3", "g2", "g1", "ys2", "ys1", "us2", "us1"),
    param_names=["beta1", "beta2", "beta3", "eps1", "eps2", "eps3", "eps5", "eps6",
                 "eps7", "g_star", "gamma", "lambda1", "lambda3", "phi1", "phi2",
                 "phi3", "psi", "rho1"],
    eviews_params={"beta1": -0.385976, "beta2": -1.201719, "beta3": -0.655304,
                   "eps1": -0.004256, "eps2": 0.080773, "eps3": 0.335710,
                   "eps5": 0.006106, "eps6": 0.004143, "eps7": 0.159817,
                   "g_star": 0.007490, "gamma": 0.004927, "lambda1": 3.658128,
                   "lambda3": -29.46525, "phi1": 1.201732, "phi2": -0.275133,
                   "phi3": -0.000476, "psi": 0.025673, "rho1": 0.655411},
    eviews_loglik=517.6595,
)


# ---------------------------------------------------------------- LW builders

def lw_build(p, ex, ix, k_states, nobs, dtype):
    Z = np.zeros((3, k_states), dtype=dtype)
    # IS curve
    Z[0, ix["y_star"]] = 1.0
    Z[0, ix["y_star_1"]] = -p["beta2"]
    Z[0, ix["y_star_2"]] = -p["beta3"]
    Z[0, ix["g_star_1"]] = -p["beta5"] * p["rho1"] ** 2 / 2
    Z[0, ix["g_star_2"]] = -p["beta5"] * p["rho1"] ** 2 / 2
    Z[0, ix["z_star_1"]] = -p["beta5"] / 2
    Z[0, ix["z_star_2"]] = -p["beta5"] / 2
    # Phillips curve
    Z[1, ix["u_star_1"]] = -p["gamma1"]
    Z[1, ix["y_star_1"]] = -p["gamma4"]
    Z[1, ix["y_star_2"]] = -p["gamma5"]
    # Okun's law with a fixed distributed lag of output gaps
    Z[2, ix["u_star"]] = 1.0
    Z[2, ix["y_star_1"]] = -0.8 * p["beta10"]
    Z[2, ix["y_star_2"]] = -0.3 * p["beta10"]
    Z[2, ix["y_star_3"]] = -0.2 * p["beta10"]
    Z[2, ix["y_star_4"]] = -0.1 * p["beta10"]

    d = np.zeros((3, nobs), dtype=dtype)
    d[0] = (p["beta2"] * ex["y1"] + p["beta3"] * ex["y2"]
            + p["beta5"] * ex["rint1"]).to_numpy()
    d[1] = (p["gamma1"] * ex["u1"] + (1 - p["gamma2"]) * ex["pi_exp"]
            + (p["gamma4"] + p["gamma5"]) * ex["y1"]).to_numpy()
    d[2] = (p["beta10"] * (0.8 * ex["y1"] + 0.3 * ex["y2"]
                           + 0.2 * ex["y3"] + 0.1 * ex["y4"])).to_numpy()

    obs_var = np.array([p["se_y"] ** 2, p["se_pi"] ** 2, p["se_u"] ** 2], dtype=dtype)
    # lambda_g = lambda_z = 1 for AU; z* shock scaled by 1/beta5
    state_var = np.array([p["se_y_star"] ** 2, p["se_g_star"] ** 2,
                          (p["se_z_star"] / p["beta5"]) ** 2,
                          p["se_u_star"] ** 2], dtype=dtype)
    return Z, d, obs_var, state_var


def lw_masks(ex):
    return {"y": ex[["y1", "y2", "rint1"]].isna().any(axis=1),
            "pi": ex[["u1", "pi_exp", "y1"]].isna().any(axis=1),
            "u": ex[["y1", "y2", "y3", "y4"]].isna().any(axis=1)}


def lw_frames(page, sample):
    w = page.loc[pd.Period(sample[0], freq="Q"):pd.Period(sample[1], freq="Q")]
    ex = pd.DataFrame(index=w.index)
    for k in range(1, 5):
        ex[f"y{k}"] = w["y"].shift(k)
    ex["rint1"] = w["rint"].shift(1)
    ex["u1"] = w["u"].shift(1)
    ex["pi_exp"] = w["pi_exp"]
    return w[["y", "pi", "u"]].copy(), ex


def lw_svec(page):
    # HP trend of log GDP (x100), its growth, and HP unemployment trend
    g, gs, hu = page["gdp_trend"], page["hp_g_star"], page["hp_u"]
    i = page.index[0]
    return np.array([g[i + 4], g[i + 3], g[i + 2], g[i + 1], g[i],
                     gs[i + 4], gs[i + 3], gs[i + 2], 0, 0, 0,
                     hu[i + 4], hu[i + 3]])


LW_SPEC = dict(
    page_file="lw_au_page_main.xlsx", sample=("1991Q1", "2023Q4"),
    states=AU13, shocks=["y_star", "g_star", "z_star", "u_star"],
    prior_var=0.0, build=lw_build, masks=lw_masks, frames=lw_frames, svec=lw_svec,
    param_names=["beta2", "beta3", "beta5", "beta10", "gamma1", "gamma2", "gamma4",
                 "gamma5", "rho1", "se_g_star", "se_pi", "se_u", "se_u_star",
                 "se_y", "se_y_star", "se_z_star"],
    eviews_params={"beta2": 1.170499, "beta3": -0.321016, "beta5": -0.119381,
                   "beta10": -0.326013, "gamma1": 1.708670, "gamma2": -0.441581,
                   "gamma4": 1.011120, "gamma5": -0.648726, "rho1": 2.935402,
                   "se_g_star": 0.028091, "se_pi": 1.234176, "se_u": 0.040910,
                   "se_u_star": -0.186888, "se_y": -0.561307, "se_y_star": 0.803825,
                   "se_z_star": -0.048587},
    eviews_loglik=-413.9825,
)


def run(validate=True):
    print("-- SMOG AU --")
    smog = run_smog("AU", SMOG_SPEC, validate)
    print("-- LW AU --")
    lw = run_lw("AU", LW_SPEC,
                rstar_fn=lambda sm, p: 4 * sm["g_star"] + sm["z_star"] / 2.2,
                covid_coef=None, validate=validate)
    return smog, lw


if __name__ == "__main__":
    print("== AU ==")
    run()
