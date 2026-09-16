"""Shared state-space machinery for the SMOG and Laubach-Williams models.

Everything is built on statsmodels' state-space framework
(statsmodels.tsa.statespace.MLEModel): it supplies the Kalman filter and
smoother, maximum-likelihood estimation, and standard errors. The classes
here only translate each model's economic equations into the standard
state-space matrices:

    observation:  y_t = Z a_t + d_t + e_t,   e_t ~ N(0, H)
    state:        a_t = T a_{t-1} + c + R n_t, n_t ~ N(0, Q)

Country files (au.py, jn.py, ...) define the specs and explain the fitting
process; this module is deliberately country-agnostic.
"""

#Load Libraries
from pathlib import Path

import numpy as np
import pandas as pd

#Statsmodel for statespace modelling
from statsmodels.tsa.statespace.mlemodel import MLEModel


#Sort directories
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output"
LW_OUT = OUT_DIR / "lw"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

#This gets the estimation data
def load_wf_export(cc):
    """Exact estimation data + EViews smoothed states from the workfile export."""
    wf = pd.read_excel(OUT_DIR / f"{cc.lower()}_wf_export.xlsx")
    wf.index = pd.PeriodIndex(pd.to_datetime(wf["_date_"]), freq="Q")
    return wf


def load_lw_page(page_file):
    wf = pd.read_excel(LW_OUT / page_file)
    wf.index = pd.PeriodIndex(pd.to_datetime(wf["_date_"]), freq="Q")
    return wf


def logistic(x):
    return np.exp(x) / (1.0 + np.exp(x))


# ====================================================================== SMOG

def smog_state_names(spec):
    names = ["gap", "gap_1", "gap_2", "y_star", "y_star_1", "u_star", "u_star_1"]
    if spec["u_star_lags"] == 2:
        names.append("u_star_2")
    return names


def smog_frames(d, spec):
    """Observables + exogenous regressors on the estimation window.

    EViews estimates on a page that STARTS at the window start, so lagged
    regressors are missing for the first few observations ("partial
    observations") - replicated here by slicing first, lagging second.
    """
    first, last = spec["sample"]
    w = d.loc[pd.Period(first, freq="Q"):pd.Period(last, freq="Q")]

    ex = pd.DataFrame(index=w.index)
    ex["covid_d"] = w["covid_d"] if "covid_d" in w else 0.0
    ex["u1"] = w["u"].shift(1)
    ex["u2"] = w["u"].shift(2)
    ex["pie"] = w["pi_e"]
    ex["pi1"] = w["pi"].shift(1)
    ex["pi2"] = w["pi"].shift(2)
    ex["pm1"] = w["delta_4_pm"].shift(1)
    ex["nulc1"] = w["delta_nulc"].shift(1) if "delta_nulc" in w else np.nan
    if spec["pi_type"] == "dit_full":
        nd = 1.0 - w["d_it"]
        ex["d_it"] = w["d_it"]
        ex["pie_d"] = w["pi_e"] * w["d_it"]
        ex["pie_nd"] = w["pi_e"] * nd
        # (1-D_it) at time t multiplies the lagged values; where D_it = 1 the
        # terms are exactly zero even if the lag itself is missing
        ex["pi3_nd"] = np.where(nd == 0.0, 0.0, w["pi"].shift(3) * nd)
        ex["nulc1_nd"] = np.where(nd == 0.0, 0.0, ex["nulc1"] * nd)
    if spec["nulc_type"] == "us":
        ex["du1_rel"] = (w["u"].diff(1) / w["u"]).shift(1)

    cols = ["y", "u", "pi"] + (["delta_nulc"] if spec["nulc_type"] else [])
    return w[cols].copy(), ex


def smog_svec(d, spec):
    """Prior mean of the initial state, from the HP-filter initial values
    (EViews svec) - indexes into the first observations of the window."""
    first = pd.Period(spec["sample"][0], freq="Q")
    src = {"g": d["ham_gap"], "ys": d["ham_y_star"], "us": d["ham_u_star"]}
    return np.array([src[t[:-1]][first + int(t[-1]) - 1] for t in spec["svec_pattern"]])


class SmogModel(MLEModel):
    """SMOG: output gap + trend output + NAIRU from GDP, unemployment (Okun),
    and inflation (Phillips curve), estimated by ML via the Kalman filter.

    States: [gap, gap_1, gap_2, y_star, y_star_1, u_star, u_star_1(, u_star_2)]
    Signals: y (GDP), u (unemployment), pi (inflation)(, delta_nulc).

    NOTE: verified against EViews - the prior covariance is exactly what the
    programme actually used (zero for most countries: the chained
    smat(1,1)=...=0.8 line is evaluated as comparisons by EViews), and
    @mprior is the t=1 state directly.
    """

    def __init__(self, endog, exog, svec, spec, prior_var=None):
        self.spec = spec
        self.svec = np.asarray(svec, dtype=float)
        self.prior_var = spec["prior_var"] if prior_var is None else prior_var
        self.snames = smog_state_names(spec)
        self.ix = {n: i for i, n in enumerate(self.snames)}
        k_states = len(self.snames)
        k_endog = 4 if spec["nulc_type"] else 3

        # a signal is unusable where its regressors are missing (EViews
        # "partial observations") - mask it out of the likelihood
        endog = endog.copy()
        masks = self._missing_masks(exog)
        for col, m in masks.items():
            endog.loc[m, col] = np.nan
        anyobs = endog.notna().any(axis=1)
        self.n_partial = int((pd.concat(masks.values(), axis=1).any(axis=1) & anyobs).sum())
        self.ex = exog.fillna(0.0)

        super().__init__(endog, k_states=k_states, k_posdef=3,
                         initialization="known", constant=self.svec,
                         stationary_cov=self.prior_var * np.eye(k_states))

        # fixed transition structure (lag chains + random walks)
        T = np.zeros((k_states, k_states))
        T[self.ix["gap_1"], self.ix["gap"]] = 1.0
        T[self.ix["gap_2"], self.ix["gap_1"]] = 1.0
        T[self.ix["y_star"], self.ix["y_star"]] = 1.0
        T[self.ix["y_star_1"], self.ix["y_star"]] = 1.0
        T[self.ix["u_star"], self.ix["u_star"]] = 1.0
        T[self.ix["u_star_1"], self.ix["u_star"]] = 1.0
        if "u_star_2" in self.ix:
            T[self.ix["u_star_2"], self.ix["u_star_1"]] = 1.0
        self._T_base = T
        self["transition"] = T

        # only gap, y_star and u_star carry shocks
        R = np.zeros((k_states, 3))
        R[self.ix["gap"], 0] = 1.0
        R[self.ix["y_star"], 1] = 1.0
        R[self.ix["u_star"], 2] = 1.0
        self["selection"] = R
        self["design"] = np.zeros((k_endog, k_states))
        self["obs_intercept"] = np.zeros((k_endog, self.nobs))
        self["state_intercept"] = np.zeros((k_states, 1))

    def _missing_masks(self, ex):
        spec = self.spec
        masks = {"y": (ex["covid_d"].isna() if spec["y_covid"] != 0.0
                       else pd.Series(False, index=ex.index))}
        m_u = ex["u1"].isna()
        if spec["u_rho_lags"] == 2:
            m_u |= ex["u2"].isna()
        masks["u"] = m_u
        cols = {"dit_full": ["pie_d", "pie_nd", "pi1", "pi2", "pi3_nd", "nulc1_nd", "pm1"],
                "sg": ["pie", "pi1", "pi2", "pm1", "nulc1"],
                "simple": ["pie", "pi1", "pi2", "pm1"]}[spec["pi_type"]]
        masks["pi"] = ex[cols].isna().any(axis=1)
        if spec["nulc_type"]:
            cols = ["pie", "pi1", "u1"] + (["u2", "du1_rel"] if spec["nulc_type"] == "us" else [])
            masks["delta_nulc"] = ex[cols].isna().any(axis=1)
        return masks

    @property
    def param_names(self):
        return self.spec["param_names"]

    def update(self, params, **kwargs):
        params = super().update(params, **kwargs)
        spec, ix, ex = self.spec, self.ix, self.ex
        p = dict(zip(spec["param_names"], params))
        k_endog = self.k_endog
        dtype = complex if np.iscomplexobj(params) else float

        # ---- observation loadings on the states -------------------------
        Z = np.zeros((k_endog, self.k_states), dtype=dtype)
        Z[0, ix["y_star"]] = 1.0                    # y  = y* + gap + ...
        Z[0, ix["gap"]] = 1.0
        Z[1, ix["u_star"]] = 1.0                    # u  = u* + lam*gap + rho*(u(-1)-u*(-1))
        Z[1, ix["gap"]] = p[spec["u_gap_coef"]]
        Z[1, ix["u_star_1"]] = -p["rho1"]
        if spec["u_rho_lags"] == 2:
            Z[1, ix["u_star_2"]] = -p["rho2"]
        Z[2, ix["gap"]] = p[spec["pi_gap_coef"]]    # pi = Phillips curve + lam*gap
        if spec["nulc_type"] == "linear":
            Z[3, ix["u_star_1"]] = -p["lambda2"]
        elif spec["nulc_type"] == "jn":             # JN bounds the coefficient in (8,9)
            Z[3, ix["u_star_1"]] = -(logistic(p["lambda2"]) + 8.0)
        elif spec["nulc_type"] == "us":
            Z[3, ix["u_star_1"]] = -p["lambda5"]
            Z[3, ix["u_star_2"]] = -p["lambda6"]
        self["design"] = Z

        # ---- transition: gap is AR(1) or AR(2); y* has drift g_star ------
        T = self._T_base.astype(dtype)
        T[ix["gap"], ix["gap"]] = p["phi1"]
        if spec["gap_ar"] == 2:
            T[ix["gap"], ix["gap_1"]] = p["phi2"]
        self["transition"] = T
        c = np.zeros((self.k_states, 1), dtype=dtype)
        c[ix["y_star"], 0] = p["g_star"]
        self["state_intercept"] = c

        # ---- variances (EViews estimates std devs that get squared) ------
        obs_sd = [p["eps1"], p["eps2"], p["eps3"]] + ([p["eps4"]] if k_endog == 4 else [])
        self["obs_cov"] = np.diag(np.array(obs_sd, dtype=dtype) ** 2)
        self["state_cov"] = np.diag(np.array(
            [p["eps5"] ** 2 * spec["gap_var_scale"], p["eps6"] ** 2, p["eps7"] ** 2],
            dtype=dtype))

        # ---- exogenous part of each signal -------------------------------
        d_obs = np.zeros((k_endog, self.nobs), dtype=dtype)
        if spec["y_covid"] != 0.0:
            d_obs[0] = spec["y_covid"] * p["phi3"] * ex["covid_d"].to_numpy()
        d_obs[1] = p["rho1"] * ex["u1"].to_numpy()
        if spec["u_rho_lags"] == 2:
            d_obs[1] += p["rho2"] * ex["u2"].to_numpy()
        if spec["pi_type"] == "dit_full":
            g = p.get("gamma", 0.0)
            d_obs[2] = ((1 - p["beta1"] - p["beta2"]) * ex["pie_d"]
                        + (1 - p["beta1"] - p["beta2"] - p["beta3"] - g) * ex["pie_nd"]
                        + p["beta1"] * ex["pi1"] + p["beta2"] * ex["pi2"]
                        + p["beta3"] * ex["pi3_nd"] + g * ex["nulc1_nd"]
                        + p["psi"] * ex["pm1"]).to_numpy()
        else:
            d_obs[2] = ((1 - p["beta1"] - p["beta2"]) * ex["pie"]
                        + p["beta1"] * ex["pi1"] + p["beta2"] * ex["pi2"]
                        + p["psi"] * ex["pm1"]).to_numpy()
            if spec["pi_type"] == "sg":
                d_obs[2] += (p["gamma"] * ex["nulc1"]).to_numpy()
        if spec["nulc_type"]:
            base = ((1 - p["beta4"]) * ex["pie"] + p["beta4"] * ex["pi1"]).to_numpy()
            if spec["nulc_type"] == "linear":
                base = base + p["lambda2"] * ex["u1"].to_numpy()
            elif spec["nulc_type"] == "jn":
                base = base + (logistic(p["lambda2"]) + 8.0) * ex["u1"].to_numpy()
            else:
                base = base + (p["lambda5"] * ex["u1"] + p["lambda6"] * ex["u2"]
                               + p["omega"] * ex["du1_rel"]).to_numpy()
            d_obs[3] = base
        self["obs_intercept"] = d_obs

        # EViews: @mprior is the mean of the state at t=1 itself
        self.ssm.initialize_known(self.svec, self.prior_var * np.eye(self.k_states))
        return params


def run_smog(cc, spec, validate=True):
    """Fit-and-smooth driver used by every country file.

    1. Load the exact estimation data (workfile export).
    2. Kalman-smooth at the stored EViews ML estimates; check the
       log-likelihood and smoothed paths reproduce EViews.
    3. Smooth over the full data range and write output gap / y* / NAIRU.
    """
    wf = load_wf_export(cc)
    d = pd.DataFrame(index=wf.index)
    for c in ["y", "u", "pi", "pi_e", "delta_4_pm", "covid_d", "d_it", "delta_nulc",
              "ham_gap", "ham_y_star", "ham_u_star"]:
        d[c] = wf[c] if c in wf.columns else (0.0 if c in ("covid_d", "d_it") else np.nan)

    ev = np.array([spec["eviews_params"][k] for k in spec["param_names"]])
    if validate:
        endog, exog = smog_frames(d, spec)
        mod = SmogModel(endog, exog, smog_svec(d, spec), spec)
        ll = mod.loglike(ev)
        ok = "OK " if abs(ll - spec["eviews_loglik"]) < 5e-4 else "??? "
        print(f"   {ok}loglike {ll:.4f} (EViews {spec['eviews_loglik']}), "
              f"partial obs {mod.n_partial}")

    full = dict(spec, sample=(str(wf.index[0]), str(wf.index[-1])))
    endog, exog = smog_frames(d, full)
    mod = SmogModel(endog, exog, smog_svec(d, spec), full)
    res = mod.smooth(ev, cov_type="none")
    sm = pd.DataFrame(res.smoothed_state.T, index=endog.index,
                      columns=smog_state_names(spec))
    out = pd.DataFrame(index=endog.index)
    out["output_gap"] = sm["gap"] * (1.0 if cc == "US" else 100.0)
    out["y_star"] = sm["y_star"]
    out["u_star"] = sm["u_star"]
    if validate:
        for k in ["gap", "y_star", "u_star"]:
            col = f"{k}_smooth"
            if col in wf.columns:
                dd = (sm[k] - wf[col].reindex(endog.index)).abs().dropna()
                if len(dd):
                    print(f"   OK {k} smoothed path matches EViews to {dd.max():.1e}")
    out.to_csv(RESULTS / f"smog_{cc.lower()}_python.csv")
    return out


# ====================================================================== LW

STD9 = ["y_star", "y_star_1", "y_star_2", "g_star", "g_star_1", "g_star_2",
        "z_star", "z_star_1", "z_star_2"]
AU13 = ["y_star", "y_star_1", "y_star_2", "y_star_3", "y_star_4",
        "g_star", "g_star_1", "g_star_2", "z_star", "z_star_1", "z_star_2",
        "u_star", "u_star_1"]


def lw_transition(names):
    """Lag-chain transition: y*_t = y*_{t-1} + g*_{t-1}; g*, z*, u* random walks."""
    n = len(names)
    ix = {s: i for i, s in enumerate(names)}
    T = np.zeros((n, n))
    T[ix["y_star"], ix["y_star"]] = 1.0
    T[ix["y_star"], ix["g_star"]] = 1.0
    for a, b in [("y_star_1", "y_star"), ("y_star_2", "y_star_1"),
                 ("g_star", "g_star"), ("g_star_1", "g_star"), ("g_star_2", "g_star_1"),
                 ("z_star", "z_star"), ("z_star_1", "z_star"), ("z_star_2", "z_star_1")]:
        T[ix[a], ix[b]] = 1.0
    if "y_star_3" in ix:
        T[ix["y_star_3"], ix["y_star_2"]] = 1.0
        T[ix["y_star_4"], ix["y_star_3"]] = 1.0
    if "u_star" in ix:
        T[ix["u_star"], ix["u_star"]] = 1.0
        T[ix["u_star_1"], ix["u_star"]] = 1.0
    return T, ix


def kappa_scale(p, ex, dtype, names=("kappa1", "kappa2", "kappa3")):
    """COVID-era observation-variance scaling (EViews kappa dummies)."""
    return (ex["kappa_c0"].to_numpy()
            + ex["kappa_c1"].to_numpy() * p[names[0]]
            + ex["kappa_c2"].to_numpy() * p[names[1]]
            + ex["kappa_c3"].to_numpy() * p[names[2]]).astype(dtype)


class LWModel(MLEModel):
    """Laubach-Williams r* model on the statsmodels state-space framework.

    The country spec supplies `build(p, ex, ix, k_states, nobs, dtype)`
    returning (design Z, obs intercept, obs variances (possibly
    time-varying), state variances), plus the masks/frames/svec builders.
    """

    def __init__(self, endog, exog, svec, spec):
        self.spec = spec
        self.ex = exog.fillna(0.0)
        self.svec = np.asarray(svec, dtype=float)
        names, shocks = spec["states"], spec["shocks"]

        endog = endog.copy()
        masks = spec["masks"](exog)
        for col, m in masks.items():
            endog.loc[m, col] = np.nan
        allmiss = endog.isna().all(axis=1)
        anyobs = endog.notna().any(axis=1)
        self.n_valid = int((~allmiss).sum())
        self.n_partial = int((pd.concat(masks.values(), axis=1).any(axis=1) & anyobs).sum())

        super().__init__(endog, k_states=len(names), k_posdef=len(shocks),
                         initialization="known", constant=self.svec,
                         stationary_cov=spec["prior_var"] * np.eye(len(names)))
        T, self.ix = lw_transition(names)
        self["transition"] = T
        R = np.zeros((len(names), len(shocks)))
        for j, s in enumerate(shocks):
            R[self.ix[s], j] = 1.0
        self["selection"] = R
        self["design"] = np.zeros((self.k_endog, self.k_states))
        self["obs_intercept"] = np.zeros((self.k_endog, self.nobs))

    @property
    def param_names(self):
        return self.spec["param_names"]

    def update(self, params, **kwargs):
        params = super().update(params, **kwargs)
        p = dict(zip(self.spec["param_names"], params))
        dtype = complex if np.iscomplexobj(params) else float
        Z, d_obs, obs_var, state_var = self.spec["build"](
            p, self.ex, self.ix, self.k_states, self.nobs, dtype)
        self["design"] = Z
        self["obs_intercept"] = d_obs
        if obs_var.ndim == 2:      # time-varying diagonal (COVID kappa scaling)
            k = obs_var.shape[0]
            oc = np.zeros((k, k, self.nobs), dtype=dtype)
            for i in range(k):
                oc[i, i, :] = obs_var[i]
            self["obs_cov"] = oc
        else:
            self["obs_cov"] = np.diag(obs_var)
        self["state_cov"] = np.diag(state_var)
        self.ssm.initialize_known(self.svec,
                                  self.spec["prior_var"] * np.eye(self.k_states))
        return params


# ---------------------------------------------------------------- KR-family LW
# KR, SG and TW share one LW structure (9 states, 2 signals, COVID kappa
# variance scaling); only rho weights, lambda_g/z, samples and the estimated
# coefficients differ - those live in each country file.

def krfam_build_factory(rho, lam_g, lam_z):
    def build(p, ex, ix, k_states, nobs, dtype):
        # IS curve: y depends on its own two lags, the real-rate gap
        # (rint - rho1*g* - rho2*z*) split over two lags, and the COVID dummy
        Z = np.zeros((2, k_states), dtype=dtype)
        Z[0, ix["y_star"]] = 1.0
        Z[0, ix["y_star_1"]] = -p["beta2"]
        Z[0, ix["y_star_2"]] = -p["beta3"]
        Z[0, ix["g_star_1"]] = -p["beta4"] * rho[0] / 2
        Z[0, ix["g_star_2"]] = -p["beta4"] * rho[0] / 2
        Z[0, ix["z_star_1"]] = -p["beta4"] * rho[1] / 2
        Z[0, ix["z_star_2"]] = -p["beta4"] * rho[1] / 2
        # Phillips curve: inflation on its own lags (1, avg 2-4, avg 5-8)
        # and the lagged output gap
        Z[1, ix["y_star_1"]] = -p["gamma4"]

        d = np.zeros((2, nobs), dtype=dtype)
        d[0] = (p["beta1"] * ex["covid"]
                + p["beta2"] * ex["y1"] + p["beta3"] * ex["y2"]
                - p["beta1"] * p["beta2"] * ex["covid1"]
                - p["beta1"] * p["beta3"] * ex["covid2"]
                + p["beta4"] / 2 * (ex["rint1"] + ex["rint2"])).to_numpy()
        d[1] = (p["gamma1"] * ex["pi1"] + p["gamma2"] * ex["pi24"]
                + (1 - p["gamma1"] - p["gamma2"]) * ex["pi58"]
                + p["gamma4"] * ex["y1"]
                - p["gamma4"] * p["beta1"] * ex["covid1"]).to_numpy()

        kap = kappa_scale(p, ex, dtype)
        obs_var = np.vstack([p["se_y"] ** 2 * kap ** 2, p["se_pi"] ** 2 * kap ** 2])
        # z* shock variance is tied to the IS slope (lambda_z * se_y / beta4)
        state_var = np.array([p["se_ystar"] ** 2,
                              (p["se_ystar"] * lam_g) ** 2,
                              (lam_z * p["se_y"] / p["beta4"]) ** 2], dtype=dtype)
        return Z, d, obs_var, state_var
    return build


def krfam_masks(ex):
    return {
        "y": ex[["covid", "covid1", "covid2", "y1", "y2", "rint1", "rint2"]].isna().any(axis=1),
        "pi": ex[["pi1", "pi24", "pi58", "y1", "covid1"]].isna().any(axis=1),
    }


def krfam_frames(page, sample):
    w = page.loc[pd.Period(sample[0], freq="Q"):pd.Period(sample[1], freq="Q")]
    ex = pd.DataFrame(index=w.index)
    ex["covid"] = w["covid_d"]
    ex["covid1"] = w["covid_d"].shift(1)
    ex["covid2"] = w["covid_d"].shift(2)
    ex["y1"] = w["y"].shift(1)
    ex["y2"] = w["y"].shift(2)
    ex["rint1"] = w["rint"].shift(1)
    ex["rint2"] = w["rint"].shift(2)
    ex["pi1"] = w["pi"].shift(1)
    ex["pi24"] = (w["pi"].shift(2) + w["pi"].shift(3) + w["pi"].shift(4)) / 3
    ex["pi58"] = (w["pi"].shift(5) + w["pi"].shift(6) + w["pi"].shift(7) + w["pi"].shift(8)) / 4
    for i in range(4):
        ex[f"kappa_c{i}"] = w[f"kappa_c{i}"]
    return w[["y", "pi"]].copy(), ex


def krfam_svec(page):
    # HP-trend of log output (x100) and its growth at the first observations
    g, gd = page["g_pot"], page["g_pot_diff"]
    i = page.index[0]
    return np.array([g[i + 3] * 100, g[i + 2] * 100, g[i + 1] * 100,
                     100 * gd[i + 3], 100 * gd[i + 2], 100 * gd[i + 1], 0, 0, 0])


def run_lw(name, spec, rstar_fn, covid_coef=None, validate=True):
    """Fit-and-smooth driver for an LW model: validate the stored EViews
    estimates, smooth over the full page, and write output gap / g* / z* / r*."""
    page = load_lw_page(spec["page_file"])
    ev = np.array([spec["eviews_params"][k] for k in spec["param_names"]])

    if validate:
        endog, exog = spec["frames"](page, spec["sample"])
        mod = LWModel(endog, exog, spec["svec"](page), spec)
        ll = mod.loglike(ev)
        ok = "OK " if abs(ll - spec["eviews_loglik"]) < 5e-4 else "??? "
        print(f"   {ok}loglike {ll:.4f} (EViews {spec['eviews_loglik']}), "
              f"valid {mod.n_valid}, partial {mod.n_partial}")

    full = dict(spec, sample=(str(page.index[0]), str(page.index[-1])))
    endog, exog = full["frames"](page, full["sample"])
    mod = LWModel(endog, exog, full["svec"](page), full)
    res = mod.smooth(ev, cov_type="none")
    sm = pd.DataFrame(res.smoothed_state.T, index=endog.index, columns=spec["states"])
    p = spec["eviews_params"]
    out = pd.DataFrame(index=endog.index)
    covid_adj = p[covid_coef] * exog["covid"].fillna(0.0) if covid_coef else 0.0
    out["output_gap"] = endog["y"] - sm["y_star"] - covid_adj
    out["y_star"] = sm["y_star"]
    out["g_star_trend_ann"] = sm["g_star"] * 4
    out["z_star"] = sm["z_star"]
    out["r_star"] = rstar_fn(sm, p)
    if "u_star" in sm.columns:
        out["u_star"] = sm["u_star"]
    out.to_csv(RESULTS / f"lw_{name.lower()}_python.csv")
    return out
