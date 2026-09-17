# Exercise real model functions without the full multi-start calibration.
#
# Load the script through the inexpensive Black-Scholes section, then load only
# later function definitions and model configuration. Long calibration loops and
# density tables are deliberately not executed. This is not a convergence test.
# %% Imports and dissertation source
# Load the source script and prepare to run only inexpensive model definitions.
import ast
from pathlib import Path
import sys

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "code" / "dissertation_full.py"
tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
namespace = {"__file__": str(SCRIPT), "__name__": "__smoke_check__"}
config = {
    "BNS_STARTS", "BNS_MODELS", "MEIXNER_STARTS", "VG_STARTS", "CGMY_STARTS",
    "NIG_STARTS", "TC_STARTS", "SV_STARTS", "N_SV_STARTS", "H_LADDER", "TOL",
}
calibration_started = False
original_argv = sys.argv
sys.argv = [str(SCRIPT)]
try:
    for node in tree.body:
        # The first expensive top-level loop fits the five Levy models.
        if (isinstance(node, ast.For)
                and isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Attribute)
                and isinstance(node.iter.func.value, ast.Name)
                and node.iter.func.value.id == "LEVY"):
            calibration_started = True
        selected = not calibration_started or isinstance(node, ast.FunctionDef)
        if isinstance(node, ast.Assign):
            selected |= any(isinstance(t, ast.Name) and t.id in config for t in node.targets)
        if selected:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(SCRIPT), "exec"), namespace)
finally:
    sys.argv = original_argv
assert calibration_started, "Could not locate the full calibration boundary"


# %% Price validation helper
# Confirm each pricing function returns finite, nonnegative values of the expected shape.
def check_prices(prices, expected):
    prices = np.asarray(prices)
    assert prices.shape == (expected,), prices.shape
    assert np.isfinite(prices).all(), "Nonfinite prices"
    assert (prices >= 0).all(), "Negative prices"


# %% Model smoke checks
# Exercise each pricing path on a small contract sample without full calibration.
checks = 0
for label, chain, spot in (("KOSPI 200", namespace["opts"], namespace["S0"]),
                           ("S&P 500", namespace["sp"], namespace["SP_S0"])):
    # One contract from each maturity exercises the pricers' maturity grouping.
    sample = chain.groupby("ttm", sort=True).head(1).reset_index(drop=True)
    k, t, r, q, mid = (sample[c].to_numpy() for c in
                        ("strike", "ttm", "rate", "div_yld", "mid"))
    sigma = namespace["fit_bs"](chain, spot, sigma0=0.66 if label == "KOSPI 200" else 0.20)
    assert np.isfinite(sigma) and sigma > 0
    check_prices(namespace["bs_call"](k, t, r, q, sigma, S0=spot), len(sample))
    checks += 1
    for name, spec in namespace["LEVY"].items():
        # A short real optimisation also exercises objective construction and
        # parameter passing. Its values are not reportable calibrated results.
        fit = namespace["fit_levy"](spec, sample, spot, maxiter=2)
        assert fit is not None, f"{label}: no valid starting fit for {name}"
        check_prices(spec["price"](k, t, r, q, *fit.x, spot), len(sample))
        checks += 1
    for name, (objective, pricer) in namespace["BNS_MODELS"].items():
        p = namespace["BNS_STARTS"][name][0]
        assert objective(p, k, t, r, q, mid, spot) < 1e5, (label, name)
        check_prices(pricer(k, t, r, q, *p, spot), len(sample))
        checks += 1
    for name, starts in namespace["SV_STARTS"].items():
        for clock in namespace["TIME_CHANGE"]:
            fit = namespace["calibrate_sv"](label, sample, spot, name, clock,
                                             starts, n_starts=1, maxiter=2)
            assert np.isfinite(fit["RMSE"]) and fit["RMSE"] < 1e5, (label, name, clock)
            psi, pnames = namespace["LEVY_PSI"][name]
            varphi, tnames = namespace["TIME_CHANGE"][clock]
            lp, tp = [fit[p] for p in pnames], [fit[p] for p in tnames]
            prices = namespace["carr_madan_levy_sv"](k, t, r, q, psi, lp, varphi, tp, spot)
            check_prices(prices, len(sample))
            namespace["sv_moments"](float(t[0]), name, clock, lp, tp)
            checks += 1
    print(f"PASS: {label}: all 20 model pricing paths")
print(f"PASS: {checks} model/dataset checks; full calibration was not run.")
