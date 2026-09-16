"""Model FITTING for the SMOG and Laubach-Williams models - the Python
equivalent of the EViews estimation programmes (not just smoothing at stored
coefficients).

Technique (matching the EViews programmes):
  1. Starting values:
     - SMOG + LW AU: EViews' own documented starting values, parsed from the
       "Initial Values:" block of the exported coefficient tables (these were
       derived in EViews from OLS regressions on HP-filtered series).
     - Other LW models: re-derived here exactly as their programmes do it -
       an NLS fit of the IS curve on the HP/break-trend output gap, an OLS
       Phillips curve, fixed defaults for the state shock scales (0.7 / 0.1)
       and kappa = 1.
  2. Maximum likelihood on the exact same Kalman-filter likelihood
     (statsmodels), BFGS with a Nelder-Mead polish - the analogue of EViews'
     Marquardt/BFGS "legacy" sequence.
  3. Convergence check against the stored EViews estimates: achieved
     log-likelihood and parameter deviations.

Where EViews itself reported "Failure to improve" or a singular coefficient
covariance (JN/SG/TW SMOG, NZ, US SMOG, HLW), the likelihood is flat in some
directions: the optimizer can legitimately land at an equal-or-better
log-likelihood with somewhat different parameters there.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent))
from statespace import (HERE, OUT_DIR, LW_OUT, SmogModel, LWModel,
                        smog_frames, smog_svec, load_wf_export, load_lw_page)


# ---------------------------------------------------------------- start values

ALIASES = {"epsilon": "eps"}


def parse_initial_values(csv_path, param_names):
    """Parse the 'Initial Values:' block EViews prints in its output table."""
    txt = Path(csv_path).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Initial Values:(.*?)User prior", txt, re.S)
    if not m:
        return None
    vals = {}
    # the CSV wraps lines mid-entry; strip quotes/commas/newlines before matching
    block = re.sub(r'[",\n]', " ", m.group(1))
    for name, num, val in re.findall(r"([A-Z_]+)\((\d+)\)\s*=\s*(-?[\d.]+(?:[Ee][+-]?\d+)?)",
                                     block):
        base = ALIASES.get(name.lower(), name.lower())
        key = f"{base}{num}" if f"{base}{num}" in param_names else base
        if key in param_names:
            vals[key] = float(val)
    missing = [p for p in param_names if p not in vals]
    if missing:
        raise ValueError(f"missing starts for {missing} in {csv_path}")
    return np.array([vals[p] for p in param_names])


def _nls(resid_fn, n_params):
    return least_squares(resid_fn, x0=np.zeros(n_params)).x


def krfam_starts(page, spec):
    """KR/SG/TW LW starting values, as in their programmes:
    NLS IS curve on the HP output gap, OLS Phillips curve, se_ystar=0.7."""
    w = page
    gap, covid, infl = w["y_gap"], w["covid_d"], w["infl"]
    rint = w["rint"]
    dat = pd.DataFrame({
        "gap": gap, "gap1": gap.shift(1), "gap2": gap.shift(2),
        "c0": covid, "c1": covid.shift(1), "c2": covid.shift(2),
        "rr": (rint.shift(1) + rint.shift(2)) / 2,
    }).dropna()

    def resid(b):
        f = (b[0] * dat["c0"] + b[1] * (dat["gap1"] - b[0] * dat["c1"])
             + b[2] * (dat["gap2"] - b[0] * dat["c2"]) + b[3] * dat["rr"] + b[4])
        return (dat["gap"] - f).to_numpy()

    b = _nls(resid, 5)
    se_y = np.sqrt(np.mean(resid(b) ** 2))

    ph = pd.DataFrame({
        "infl": infl, "i1": infl.shift(1),
        "i24": (infl.shift(2) + infl.shift(3) + infl.shift(4)) / 3,
        "i58": (infl.shift(5) + infl.shift(6) + infl.shift(7) + infl.shift(8)) / 4,
        "gapterm": gap.shift(1) - b[0] * covid.shift(1),
    }).dropna()
    ols = sm.OLS(ph["infl"], sm.add_constant(ph[["i1", "i24", "i58", "gapterm"]])).fit()
    se_pi = np.sqrt(ols.mse_resid)

    starts = {"beta1": b[0], "beta2": b[1], "beta3": b[2], "beta4": b[3],
              "gamma1": ols.params["i1"], "gamma2": ols.params["i24"],
              "gamma4": ols.params["gapterm"],
              "kappa1": 1.0, "kappa2": 1.0, "kappa3": 1.0,
              "se_pi": se_pi, "se_y": se_y, "se_ystar": 0.7}
    return np.array([starts[p] for p in spec["param_names"]])


def jn_starts(page, spec):
    """LW JN: IS-curve NLS on the break-trend output gap; Phillips OLS."""
    gap, covid, infl, rint = page["y_gap"], page["covid_d"], page["infl"], page["rint"]
    dat = pd.DataFrame({"gap": gap, "gap1": gap.shift(1), "gap2": gap.shift(2),
                        "c0": covid, "c1": covid.shift(1), "c2": covid.shift(2),
                        "r1": rint.shift(1)}).dropna()

    def resid(b):
        f = (b[0] * dat["c0"] + b[1] * (dat["gap1"] - b[0] * dat["c1"])
             + b[2] * (dat["gap2"] - b[0] * dat["c2"]) + b[3] * dat["r1"] + b[4])
        return (dat["gap"] - f).to_numpy()

    b = _nls(resid, 5)
    se_y = np.sqrt(np.mean(resid(b) ** 2))
    ph = pd.DataFrame({"infl": infl, "i1": infl.shift(1),
                       "gapterm": gap.shift(1) - b[0] * covid.shift(1)}).dropna()
    ols = sm.OLS(ph["infl"], sm.add_constant(ph[["i1", "gapterm"]])).fit()
    starts = {"beta1": b[0], "beta2": b[1], "beta3": b[2], "beta4": b[3],
              "gamma2": ols.params["i1"], "gamma3": ols.params["gapterm"],
              "kappa1": 1.0, "kappa2": 1.0, "kappa3": 1.0,
              "se_pi": np.sqrt(ols.mse_resid), "se_y": se_y, "se_y_star": 0.7}
    return np.array([starts[p] for p in spec["param_names"]])


def us_starts(page, spec):
    """LW US stage 3: NLS IS curve, Phillips OLS with oil and import terms,
    then the dr(...) initial mapping from the programme (incl. dr6 floor)."""
    gap, covid, infl, rint = page["y_gap"], page["covid_d"], page["infl"], page["rint"]
    dat = pd.DataFrame({"gap": gap, "gap1": gap.shift(1), "gap2": gap.shift(2),
                        "c0": covid, "c1": covid.shift(1), "c2": covid.shift(2),
                        "rr": (rint.shift(1) + rint.shift(2)) / 2}).dropna()

    def resid(b):
        f = (b[0] * dat["c0"] + b[1] * (dat["gap1"] - b[0] * dat["c1"])
             + b[2] * (dat["gap2"] - b[0] * dat["c2"]) + b[3] * dat["rr"] + b[4])
        return (dat["gap"] - f).to_numpy()

    b = _nls(resid, 5)
    s_is = np.sqrt(np.mean(resid(b) ** 2))
    ph = pd.DataFrame({
        "infl": infl, "i1": infl.shift(1),
        "i24": (infl.shift(2) + infl.shift(3) + infl.shift(4)) / 3,
        "i58": (infl.shift(5) + infl.shift(6) + infl.shift(7) + infl.shift(8)) / 4,
        "gapterm": gap.shift(1) - b[0] * covid.shift(1),
        "oilterm": page["poil"].shift(1) - infl.shift(1),
        "impterm": page["pimp"].shift(1),
    }).dropna()
    ols = sm.OLS(ph["infl"], ph[["i1", "i24", "i58", "gapterm", "oilterm", "impterm"]]).fit()
    s_ph = np.sqrt(ols.mse_resid)
    dr6 = max(ols.params["gapterm"], 0.025)         # the programme's b_y floor
    starts = {"dr1": b[1], "dr2": b[2], "dr3": b[3], "dr4": ols.params["i1"],
              "dr5": ols.params["i24"], "dr6": dr6, "dr7": ols.params["oilterm"],
              "dr8": ols.params["impterm"], "dr9": 1.0, "dr10": s_is,
              "dr11": s_ph, "dr12": 0.7, "dr13": b[0],
              "dr14": 1.0, "dr15": 1.0, "dr16": 1.0}
    return np.array([starts[p] for p in spec["param_names"]])


def hlw_starts(page, spec):
    """HLW US: Phillips first (with beta1 at its zero default, as the
    programme does), then the IS-curve NLS; shock scales start at 0.1."""
    gap, covid, infl, rint = (page["output_gap_initial"], page["covid_d"],
                              page["infl"], page["rint"])
    ph = pd.DataFrame({"infl": infl, "i1": infl.shift(1),
                       "i24": (infl.shift(2) + infl.shift(3) + infl.shift(4)) / 3,
                       "gap1": gap.shift(1)}).dropna()

    def ph_resid(g):
        return (ph["infl"] - (g[0] * ph["i1"] + (1 - g[0]) * ph["i24"]
                              + g[1] * ph["gap1"])).to_numpy()

    g = _nls(ph_resid, 2)
    se_pi = np.sqrt(np.mean(ph_resid(g) ** 2))

    dat = pd.DataFrame({"gap": gap, "gap1": gap.shift(1), "gap2": gap.shift(2),
                        "c0": covid, "c1": covid.shift(1), "c2": covid.shift(2),
                        "r1": rint.shift(1), "r2": rint.shift(2)}).dropna()

    def is_resid(b):
        f = (b[0] * dat["c0"] + b[1] * (dat["gap1"] - b[0] * dat["c1"])
             + b[2] * (dat["gap2"] - b[0] * dat["c2"])
             + b[3] / 2 * dat["r1"] + b[3] / 2 * dat["r2"])
        return (dat["gap"] - f).to_numpy()

    b = _nls(is_resid, 4)
    starts = {"beta1": b[0], "beta2": b[1], "beta3": b[2], "beta4": b[3],
              "gamma1": g[0], "gamma2": g[1],
              "kappa1": 1.0, "kappa2": 1.0, "kappa3": 1.0, "rho1": 1.0,
              "se_g_star": 0.1, "se_pi": se_pi,
              "se_y": np.sqrt(np.mean(is_resid(b) ** 2)),
              "se_y_star": 0.1, "se_z_star": 0.1}
    return np.array([starts[p] for p in spec["param_names"]])


LW_START_BUILDERS = {"KR": krfam_starts, "SG": krfam_starts, "TW": krfam_starts,
                     "JN": jn_starts, "US": us_starts, "HLW_US": hlw_starts}


# ---------------------------------------------------------------- MLE drivers

def _mle(mod, start, spec, label):
    """BFGS -> Nelder-Mead polish -> BFGS (the analogue of EViews'
    Marquardt/BFGS sequence), then compare with the stored EViews optimum."""
    # Rotate optimizers until the likelihood stops improving - the EViews
    # programmes note the same trick ("legacy is best, but gets stuck, so I
    # double optimise using BFGS"). Nelder-Mead and Powell are derivative-free
    # and escape the plateaus where BFGS stalls.
    fit = mod.fit(start_params=start, method="bfgs", maxiter=5000, disp=False,
                  cov_type="none")
    for _ in range(8):
        prev = fit.llf
        for method, iters in [("nm", 20000), ("bfgs", 5000),
                              ("powell", 5000), ("bfgs", 5000)]:
            trial = mod.fit(start_params=fit.params, method=method,
                            maxiter=iters, disp=False, cov_type="none")
            if trial.llf > fit.llf:      # keep only genuine improvements
                fit = trial
        if fit.llf - prev < 1e-6:        # converged
            break

    # If we stalled below EViews' likelihood, the optimizer is on a plateau:
    # try a few small seeded perturbations of the best point (multi-start)
    # and keep whatever improves. EViews' Marquardt steps walk plateaus
    # differently, so this recovers its optimum where plain BFGS/NM stall.
    rng = np.random.default_rng(12345)
    tries = 0
    while fit.llf < spec["eviews_loglik"] - 1e-3 and tries < 5:
        tries += 1
        jitter = fit.params * (1 + 0.05 * rng.standard_normal(len(fit.params)))
        try:
            trial = mod.fit(start_params=jitter, method="bfgs", maxiter=5000,
                            disp=False, cov_type="none")
            trial = mod.fit(start_params=trial.params, method="nm", maxiter=20000,
                            disp=False, cov_type="none")
            trial = mod.fit(start_params=trial.params, method="bfgs", maxiter=5000,
                            disp=False, cov_type="none")
            if trial.llf > fit.llf:
                fit = trial
        except Exception:
            continue
    ev = np.array([spec["eviews_params"][k] for k in spec["param_names"]])
    ll_ev = spec["eviews_loglik"]
    # variance parameters enter squared, so their sign is irrelevant
    py, evv = np.asarray(fit.params, dtype=float).copy(), ev.copy()
    for i, n in enumerate(spec["param_names"]):
        if n.startswith(("eps", "se_")) or n in ("dr10", "dr11", "dr12"):
            py[i], evv[i] = abs(py[i]), abs(evv[i])
    dev = np.abs(py - evv)
    print(f"   {label}: loglike {fit.llf:.4f} vs EViews {ll_ev} "
          f"(gain {fit.llf - ll_ev:+.4f}); max param dev {dev.max():.4g} "
          f"({spec['param_names'][int(dev.argmax())]})")
    return fit


def fit_smog(cc, spec):
    """Fit a SMOG model by MLE from EViews' own starting values."""
    wf = load_wf_export(cc)
    d = pd.DataFrame(index=wf.index)
    for c in ["y", "u", "pi", "pi_e", "delta_4_pm", "covid_d", "d_it", "delta_nulc",
              "ham_gap", "ham_y_star", "ham_u_star"]:
        d[c] = wf[c] if c in wf.columns else (0.0 if c in ("covid_d", "d_it") else np.nan)
    endog, exog = smog_frames(d, spec)
    mod = SmogModel(endog, exog, smog_svec(d, spec), spec)
    start = parse_initial_values(OUT_DIR / f"{cc.lower()}_ss1_output.csv",
                                 spec["param_names"])
    return _mle(mod, start, spec, f"SMOG {cc}")


def fit_lw(name, spec):
    """Fit an LW model by MLE from EViews' documented starts (AU) or the
    programme's OLS/NLS-derived starting values (other countries)."""
    page = load_lw_page(spec["page_file"])
    endog, exog = spec["frames"](page, spec["sample"])
    mod = LWModel(endog, exog, spec["svec"](page), spec)
    if name == "AU":
        start = parse_initial_values(LW_OUT / "lw_au_ss1_output.csv",
                                     spec["param_names"])
    else:
        start = LW_START_BUILDERS[name](page, spec)
    return _mle(mod, start, spec, f"LW {name}")
