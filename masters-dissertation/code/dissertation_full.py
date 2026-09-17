# %% Setup and input data
# Load dependencies, set file paths, and read the two option datasets.

# Every numerical result reported in the dissertation, in close to the order in which the
# results appear.

#     0. Pricing       -- overview of functions used repeatedly,
#                      -- characteristic functions and the Carr-Madan transform
#     1. Data          -- just focusing on how I pruned the data - not data pulling
#     2. Black-Scholes -- both the full model and per maturity
#     3. Levy models   -- Meixner, VG, CGMY, NIG and GH 
#     4. Per maturity  -- the same five Levy models fitted by maturity
#     5. BNS           -- Gamma-OU and IG-OU
#     6. Time change   -- the twelve Levy models with stochastic time process added on
#     7. Moments       -- variance and kurtosis of each fit
#     8. Volatility    -- the implied volatility
#     9. Validation    -- every model above refitted to Schoutens' S&P 500 chain

# The only inputs are KOSPI 200 option data.csv, the
# pruned 212-contract chain, and S&P 2002 validation data.xlsx for Section 9.
# Running the whole file takes several hours.

# The libraries used throughout this dissertation
import argparse
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.special import gamma as gamma_fn, gammaln, kv, loggamma
from scipy.stats import norm

# Resolve inputs from this script or from the repository when running cells.
try:
    CODE_DIR = Path(__file__).resolve().parent
except NameError:
    CODE_DIR = next(
        (candidate for parent in (Path.cwd(), *Path.cwd().parents)
         for candidate in (
             parent / "code",
             parent / "masters-dissertation" / "code",
             parent / "michaelwjones" / "masters-dissertation" / "code",
         ) if (candidate / "KOSPI 200 option data.csv").is_file()),
        None,
    )
    if CODE_DIR is None:
        raise FileNotFoundError("Open the repository before running dissertation cells")
PRUNED_CHAIN = CODE_DIR / "KOSPI 200 option data.csv"
SCHOUTENS_DATA = CODE_DIR / "S&P 2002 validation data.xlsx"


# %% Validate Chain
# Reject malformed option contracts.
def validate_chain(o, spot_column, source):
    # Check required columns.
    required = ["strike", "ttm", "rate", "div_yld", "mid", spot_column]
    missing = set(required) - set(o.columns)
    if missing:
        raise ValueError(f"{source}: missing columns {sorted(missing)}")
    if o.empty:
        raise ValueError(f"{source}: no contracts found")
    # Require finite inputs.
    values = o[required].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"{source}: required numeric data contains missing or infinite values")
    if (values[["strike", "ttm", "mid", spot_column]] <= 0).any().any():
        raise ValueError(f"{source}: strikes, maturities, prices and spot must be positive")
    if values[spot_column].nunique() != 1:
        raise ValueError(f"{source}: expected a single spot price")
    o = o.copy()
    o[required] = values
    # Return validated contracts.
    return o.reset_index(drop=True), float(values[spot_column].iloc[0])


# %% Load Chain
# Read KOSPI option contracts.
def load_chain():
    o = pd.read_csv(PRUNED_CHAIN, parse_dates=["expiry_date", "snapshot_date"])
    for column in ("expiry_date", "snapshot_date"):
        o[column] = pd.to_datetime(o[column], errors="raise")
        if o[column].isna().any():
            raise ValueError(f"{PRUNED_CHAIN}: missing {column}")
    return validate_chain(o, "spot_price", PRUNED_CHAIN)


# %% Load Sp500
# Read S&P validation contracts.
def load_sp500():
    o = pd.read_excel(SCHOUTENS_DATA, sheet_name="Schoutens Data", skiprows=7)
    return validate_chain(o, "spot", SCHOUTENS_DATA)


# %% Input validation
# Parse command-line options and validate the bundled option chains.
parser = argparse.ArgumentParser(description="Dissertation option-pricing analysis")
parser.add_argument("--check-inputs", action="store_true",
                    help="Validate both bundled datasets and exit without calibration")
args = parser.parse_args([] if "__file__" not in globals() else None)

# Check both inputs before starting hours of numerical work.
opts, S0 = load_chain()
sp, SP_S0 = load_sp500()
print(f"KOSPI 200: {len(opts)} contracts; input: {PRUNED_CHAIN}")
print(f"Schoutens S&P 500: {len(sp)} contracts; input: {SCHOUTENS_DATA}")
if args.check_inputs:
    print("Input checks passed. No calibrations were run.")
    raise SystemExit(0)

# %% Pricing machinery
# Define characteristic functions and Fourier-based option pricing routines.
# 0. PRICING MACHINERY
# The characteristic functions and the Carr-Madan transform. Every price computed
# below comes through this section.

CM_ALPHA = 0.75      # Carr-Madan damping
N_GRID = 4096        # quadrature points
V_MAX = 200.0        # upper integration bound


# ---------------------------------------------------------------------------
# 0.1  The Levy models of Chapter 6: CGMY, VG, NIG and GH.
CM_ALPHA = 0.75      # Carr-Madan damping (Schoutens Ch.2)
N_GRID = 4096       
V_MAX = 200.0      


# CGMY model input
# %% Cgmy Char Exponent
# Compute model return transform.
def cgmy_char_exponent(u, C, G, M, Y):
    return C * gamma_fn(-Y) * ((M - 1j * u) ** Y - M**Y + (G + 1j * u) ** Y - G**Y)

#Define the m drift parameter
# %% M New Cgmy
# Set risk-neutral model drift.
def m_new_cgmy(C, G, M, Y, r, q):
    return r - q - C * gamma_fn(-Y) * ((M - 1) ** Y - M**Y + (G + 1) ** Y - G**Y)

#Now produce the Carr and Madan, with parameters as inputs
# %% Carr Madan Batch
# Fourier-price option contracts.
def carr_madan_batch(strikes, ttms, rates, divs, C, G, M, Y, S0,
                     alpha=CM_ALPHA, n_grid=N_GRID, v_max=V_MAX):

    # Align contract arrays.
    strikes = np.asarray(strikes, dtype=float)
    ttms = np.asarray(ttms, dtype=float)
    rates = np.asarray(rates, dtype=float)
    divs = np.asarray(divs, dtype=float)
    v = np.linspace(1e-10, v_max, n_grid)[:, None] 
    log_k = np.log(strikes)[None, :]                
    prices = np.empty(len(strikes))

    # Reuse Fourier denominator.
    denom = alpha**2 + alpha - v**2 + 1j * (2 * alpha + 1) * v

    # Price each maturity separately.
    for T in np.unique(ttms):
        sel = ttms == T
        r, q = rates[sel][0], divs[sel][0]
        u = v - (alpha + 1) * 1j
        cf = np.exp(1j * u * (np.log(S0) + m_new_cgmy(C, G, M, Y, r, q) * T)
                    + T * cgmy_char_exponent(u, C, G, M, Y))          # (N, 1)
        integrand = np.real(np.exp(-1j * v * log_k[:, sel]) * np.exp(-r * T) * cf / denom)
        prices[sel] = np.exp(-alpha * log_k[0, sel]) / np.pi * np.trapezoid(integrand, v[:, 0], axis=0)

    # Collect contract prices.
    return prices


# ----------------------------------------------------------------------
# Variance Gamma

#Same as CGMY - define the characteristic exponent
# %% Vg Char Exponent
# Compute model return transform.
def vg_char_exponent(u, C, G, M):
    return C * np.log(G * M / (G * M + (M - G) * 1j * u + u**2))

#Then define the m parameter
# %% M New Vg
# Set risk-neutral model drift.
def m_new_vg(C, G, M, r, q):
    return r - q + C * np.log((M - 1) * (G + 1) / (M * G))

#Now again define the carr and madan function process - just like CGMY
# %% Carr Madan Batch Vg
# Fourier-price option contracts.
def carr_madan_batch_vg(strikes, ttms, rates, divs, C, G, M, S0,
                        alpha=CM_ALPHA, n_grid=N_GRID, v_max=V_MAX):
    # Align contract arrays.
    strikes = np.asarray(strikes, dtype=float)
    ttms = np.asarray(ttms, dtype=float)
    rates = np.asarray(rates, dtype=float)
    divs = np.asarray(divs, dtype=float)

    v = np.linspace(1e-10, v_max, n_grid)[:, None]
    log_k = np.log(strikes)[None, :]
    prices = np.empty(len(strikes))
    denom = alpha**2 + alpha - v**2 + 1j * (2 * alpha + 1) * v

    # Price each maturity separately.
    for T in np.unique(ttms):
        sel = ttms == T
        r, q = rates[sel][0], divs[sel][0]
        u = v - (alpha + 1) * 1j
        cf = np.exp(1j * u * (np.log(S0) + m_new_vg(C, G, M, r, q) * T)
                    + T * vg_char_exponent(u, C, G, M))
        integrand = np.real(np.exp(-1j * v * log_k[:, sel]) * np.exp(-r * T) * cf / denom)
        prices[sel] = np.exp(-alpha * log_k[0, sel]) / np.pi * np.trapezoid(integrand, v[:, 0], axis=0)

    # Collect contract prices.
    return prices

#Define the RMSE calculation for the VG process, returning 1e6 at the boundary, 
# as a boundary condition
# %% Rmse Objective Vg
# Score model pricing errors.
def rmse_objective_vg(params, strikes, ttms, rates, divs, mids, S0):
    C, G, M = params
    # Reject invalid parameters.
    if C <= 1e-6 or G <= 1e-6 or M <= 1.0 + 1e-6:
        return 1e6
    # Price candidate parameters.
    try:
        model = carr_madan_batch_vg(strikes, ttms, rates, divs, C, G, M, S0)
    except Exception:
        return 1e6
    if not np.all(np.isfinite(model)) or np.any(model < 0):
        return 1e6
    # Measure pricing error.
    return float(np.sqrt(np.mean((model - np.asarray(mids)) ** 2)))


# ---------------------------------------------------------------------------
# Normal Inverse Gaussian 

#Again, same process, define characteristic exponent
# %% Nig Char Exponent
# Compute model return transform.
def nig_char_exponent(u, a, b, d):
    return -d * (np.sqrt(a**2 - (b + 1j * u) ** 2) - np.sqrt(a**2 - b**2))

#find the m drift parameter
# %% M New Nig
# Set risk-neutral model drift.
def m_new_nig(a, b, d, r, q):
    return r - q + d * (np.sqrt(a**2 - (b + 1) ** 2) - np.sqrt(a**2 - b**2))

#Define the carr and madan approach - same as before
# %% Carr Madan Batch Nig
# Fourier-price option contracts.
def carr_madan_batch_nig(strikes, ttms, rates, divs, a, b, d, S0,
                         alpha=CM_ALPHA, n_grid=N_GRID, v_max=V_MAX):
    # Align contract arrays.
    strikes = np.asarray(strikes, dtype=float)
    ttms = np.asarray(ttms, dtype=float)
    rates = np.asarray(rates, dtype=float)
    divs = np.asarray(divs, dtype=float)

    v = np.linspace(1e-10, v_max, n_grid)[:, None]
    log_k = np.log(strikes)[None, :]
    prices = np.empty(len(strikes))
    denom = alpha**2 + alpha - v**2 + 1j * (2 * alpha + 1) * v

    # Price each maturity separately.
    for T in np.unique(ttms):
        sel = ttms == T
        r, q = rates[sel][0], divs[sel][0]
        u = v - (alpha + 1) * 1j
        cf = np.exp(1j * u * (np.log(S0) + m_new_nig(a, b, d, r, q) * T)
                    + T * nig_char_exponent(u, a, b, d))
        integrand = np.real(np.exp(-1j * v * log_k[:, sel]) * np.exp(-r * T) * cf / denom)
        prices[sel] = np.exp(-alpha * log_k[0, sel]) / np.pi * np.trapezoid(integrand, v[:, 0], axis=0)

    # Collect contract prices.
    return prices

#Now the RMSE objective - note the restrictions are present too
# %% Rmse Objective Nig
# Score model pricing errors.
def rmse_objective_nig(params, strikes, ttms, rates, divs, mids, S0):
    a, b, d = params
    # Reject invalid parameters.
    if a <= 1e-6 or d <= 1e-6 or abs(b) >= a - 1e-6 or abs(b + 1) >= a - 1e-6:
        return 1e6
    # Price candidate parameters.
    try:
        model = carr_madan_batch_nig(strikes, ttms, rates, divs, a, b, d, S0)
    except Exception:
        return 1e6
    if not np.all(np.isfinite(model)) or np.any(model < 0):
        return 1e6
    # Measure pricing error.
    return float(np.sqrt(np.mean((model - np.asarray(mids)) ** 2)))


# ---------------------------------------------------------------------------
# Generalized Hyperbolic (Schoutens 5.3.11). Four parameters (alpha, beta,
# delta, nu);
# Unlike the other families here, GH's characteristic function is NOT of the
# form exp(t * psi(u)) with psi elementary: raising it to the power t requires phi_t(u) = (phi_1(u))^t.
# That is handled below by taking t*log(phi_1(u)) with a complex logarithm.

#Define characteristic function
# %% Gh Log Char
# Compute model return transform.
def gh_log_char(u, a, b, d, nu):
    s_u = np.sqrt(a**2 - (b + 1j * u) ** 2)
    s_0 = np.sqrt(a**2 - b**2)
    ratio = kv(nu, d * s_u) / kv(nu, d * s_0)
    val = (nu / 2) * np.log((a**2 - b**2) / (a**2 - (b + 1j * u) ** 2)) + np.log(ratio)
    if np.ndim(val) and np.shape(val)[0] > 1:
        val = np.real(val) + 1j * np.unwrap(np.imag(val), axis=0)
    return val

#Now get the m_new again, like the other 
# %% M New Gh
# Set risk-neutral model drift.
def m_new_gh(a, b, d, nu, r, q):
    s_1 = np.sqrt(a**2 - (b + 1) ** 2)
    s_0 = np.sqrt(a**2 - b**2)
    return r - q - (
        (nu / 2) * np.log((a**2 - b**2) / (a**2 - (b + 1) ** 2))
        + np.log(kv(nu, d * s_1) / kv(nu, d * s_0))
    )

#Now define carr and madan, but the characteristic formulation differs by taking it to the power
# %% Carr Madan Batch Gh
# Fourier-price option contracts.
def carr_madan_batch_gh(strikes, ttms, rates, divs, a, b, d, nu, S0,
                        alpha=CM_ALPHA, n_grid=N_GRID, v_max=V_MAX):
    # Align contract arrays.
    strikes = np.asarray(strikes, dtype=float)
    ttms = np.asarray(ttms, dtype=float)
    rates = np.asarray(rates, dtype=float)
    divs = np.asarray(divs, dtype=float)

    v = np.linspace(1e-10, v_max, n_grid)[:, None]
    log_k = np.log(strikes)[None, :]
    prices = np.empty(len(strikes))
    denom = alpha**2 + alpha - v**2 + 1j * (2 * alpha + 1) * v

    u = v - (alpha + 1) * 1j
    log_phi1 = gh_log_char(u, a, b, d, nu)      # unit-time, shared across maturities

    # Price each maturity separately.
    for T in np.unique(ttms):
        sel = ttms == T
        r, q = rates[sel][0], divs[sel][0]
        cf = np.exp(1j * u * (np.log(S0) + m_new_gh(a, b, d, nu, r, q) * T) + T * log_phi1)
        integrand = np.real(np.exp(-1j * v * log_k[:, sel]) * np.exp(-r * T) * cf / denom)
        prices[sel] = np.exp(-alpha * log_k[0, sel]) / np.pi * np.trapezoid(integrand, v[:, 0], axis=0)

    # Collect contract prices.
    return prices

#Now define the RMSE objective same as the others, with parameter boundaries included as penalty
# %% Rmse Objective Gh
# Score model pricing errors.
def rmse_objective_gh(params, strikes, ttms, rates, divs, mids, S0):
    a, b, d, nu = params
    # Reject invalid parameters.
    if a <= 1e-6 or d <= 1e-6 or abs(b) >= a - 1e-6 or abs(b + 1) >= a - 1e-6:
        return 1e6
    # Price candidate parameters.
    try:
        model = carr_madan_batch_gh(strikes, ttms, rates, divs, a, b, d, nu, S0)
    except Exception:
        return 1e6
    if not np.all(np.isfinite(model)) or np.any(model < 0):
        return 1e6
    # Measure pricing error.
    return float(np.sqrt(np.mean((model - np.asarray(mids)) ** 2)))


# Here's the CGMY objective function that was missing earlier,
#Also included are the boundaries as penalty
# %% Rmse Objective
# Score model pricing errors.
def rmse_objective(params, strikes, ttms, rates, divs, mids, S0):
    C, G, M, Y = params
    # Reject invalid parameters.
    if C <= 1e-6 or G <= 1e-6 or M <= 1.0 + 1e-6 or Y >= 2.0 - 1e-6:
        return 1e6
    # Price candidate parameters.
    try:
        model = carr_madan_batch(strikes, ttms, rates, divs, C, G, M, Y, S0)
    except Exception:
        return 1e6
    if not np.all(np.isfinite(model)) or np.any(model < 0):
        return 1e6
    # Measure pricing error.
    return float(np.sqrt(np.mean((model - np.asarray(mids)) ** 2)))


# ---------------------------------------------------------------------------
# 0.2  The BNS models Carr and Madan Approach


#First define characteristic function
# %% Bns Gamma Char Fn
# Compute model return transform.
def bns_gamma_char_fn(u, T, r, q, rho, lam, a, b, sigma0_sq, S0):
    # Use complex frequencies.
    u = np.asarray(u, dtype=complex)

    f1 = 1j * u * rho - 0.5 * (u**2 + 1j * u) * (1 - np.exp(-lam * T))
    f2 = 1j * u * rho - 0.5 * (u**2 + 1j * u)

    term1 = 1j * u * (np.log(S0) + (r - q - a * lam * rho / (b - rho)) * T)
    term2 = -0.5 * (u**2 + 1j * u) * (1 - np.exp(-lam * T)) / lam * sigma0_sq
    term3 = a / (b - f2) * (b * np.log((b - f1) / (b - 1j * u * rho)) + f2 * lam * T)

    # Combine pricing terms.
    return np.exp(term1 + term2 + term3)

#Then define carr-madan - same approach
# %% Carr Madan Batch Bns
# Fourier-price option contracts.
def carr_madan_batch_bns(strikes, ttms, rates, divs, rho, lam, a, b, sigma0_sq, S0,
                         alpha=CM_ALPHA, n_grid=N_GRID, v_max=V_MAX):
    # Align contract arrays.
    strikes = np.asarray(strikes, dtype=float)
    ttms = np.asarray(ttms, dtype=float)
    rates = np.asarray(rates, dtype=float)
    divs = np.asarray(divs, dtype=float)

    v = np.linspace(1e-10, v_max, n_grid)[:, None]
    log_k = np.log(strikes)[None, :]
    prices = np.empty(len(strikes))
    denom = alpha**2 + alpha - v**2 + 1j * (2 * alpha + 1) * v

    # Price each maturity separately.
    for T in np.unique(ttms):
        sel = ttms == T
        r, q = rates[sel][0], divs[sel][0]
        cf = bns_gamma_char_fn(v - (alpha + 1) * 1j, T, r, q,
                               rho, lam, a, b, sigma0_sq, S0)
        integrand = np.real(np.exp(-1j * v * log_k[:, sel]) * np.exp(-r * T) * cf / denom)
        prices[sel] = np.exp(-alpha * log_k[0, sel]) / np.pi * np.trapezoid(integrand, v[:, 0], axis=0)

    # Collect contract prices.
    return prices

#Now RMSE
# %% Rmse Objective Bns
# Score model pricing errors.
def rmse_objective_bns(params, strikes, ttms, rates, divs, mids, S0):
    rho, lam, a, b, sigma0_sq = params
    # Reject invalid parameters.
    if lam <= 1e-6 or a <= 1e-6 or b <= 1e-6 or sigma0_sq <= 1e-8:
        return 1e6
    if rho >= b - 1e-6:
        return 1e6
    # Price candidate parameters.
    try:
        model = carr_madan_batch_bns(strikes, ttms, rates, divs,
                                     rho, lam, a, b, sigma0_sq, S0)
    except Exception:
        return 1e6
    if not np.all(np.isfinite(model)) or np.any(model < 0):
        return 1e6
    # Measure pricing error.
    return float(np.sqrt(np.mean((model - np.asarray(mids)) ** 2)))




# The IG-OU variant. 
# %% Bns Ig Char Fn
# Compute model return transform.
def bns_ig_char_fn(u, T, r, q, rho, lam, a, b, sigma0_sq, S0):
    # Use complex frequencies.
    u = np.asarray(u, dtype=complex)

    f1 = 1j * u * rho - 0.5 * (u**2 + 1j * u) * (1 - np.exp(-lam * T))
    f2 = 1j * u * rho - 0.5 * (u**2 + 1j * u)

    drift = r - q - rho * lam * a / b * (1 - 2 * rho / b**2) ** -0.5
    term1 = 1j * u * (np.log(S0) + drift * T)
    term2 = 0.5 * (-u**2 - 1j * u) * (1 - np.exp(-lam * T)) * sigma0_sq / lam
    term3 = a * (np.sqrt(b**2 - 2 * f1) - np.sqrt(b**2 - 2j * u * rho))

    denom = np.sqrt(2 * f2 - b**2)
    term4 = (2 * a * f2 / denom
             * (np.arctan(np.sqrt((b**2 - 2j * u * rho) / (2 * f2 - b**2)))
                - np.arctan(np.sqrt((b**2 - 2 * f1) / (2 * f2 - b**2)))))

    # Combine pricing terms.
    return np.exp(term1 + term2 + term3 + term4)


# %% Carr Madan Batch Ig
# Fourier-price option contracts.
def carr_madan_batch_ig(strikes, ttms, rates, divs, rho, lam, a, b, sigma0_sq, S0,
                        alpha=CM_ALPHA, n_grid=N_GRID, v_max=V_MAX):
    # Align contract arrays.
    strikes = np.asarray(strikes, dtype=float)
    ttms = np.asarray(ttms, dtype=float)
    rates = np.asarray(rates, dtype=float)
    divs = np.asarray(divs, dtype=float)

    v = np.linspace(1e-10, v_max, n_grid)[:, None]
    log_k = np.log(strikes)[None, :]
    prices = np.empty(len(strikes))
    denom = alpha**2 + alpha - v**2 + 1j * (2 * alpha + 1) * v

    # Price each maturity separately.
    for T in np.unique(ttms):
        sel = ttms == T
        r, q = rates[sel][0], divs[sel][0]
        cf = bns_ig_char_fn(v - (alpha + 1) * 1j, T, r, q,
                            rho, lam, a, b, sigma0_sq, S0)
        integrand = np.real(np.exp(-1j * v * log_k[:, sel]) * np.exp(-r * T) * cf / denom)
        prices[sel] = np.exp(-alpha * log_k[0, sel]) / np.pi * np.trapezoid(integrand, v[:, 0], axis=0)

    # Collect contract prices.
    return prices


# %% Rmse Objective Ig
# Score model pricing errors.
def rmse_objective_ig(params, strikes, ttms, rates, divs, mids, S0):
    rho, lam, a, b, sigma0_sq = params
    # Reject invalid parameters.
    if lam <= 1e-6 or a <= 1e-6 or b <= 1e-6 or sigma0_sq <= 1e-8:
        return 1e6
    if 2 * rho >= b**2 - 1e-9:
        return 1e6
    # Price candidate parameters.
    try:
        model = carr_madan_batch_ig(strikes, ttms, rates, divs,
                                    rho, lam, a, b, sigma0_sq, S0)
    except Exception:
        return 1e6
    if not np.all(np.isfinite(model)) or np.any(model < 0):
        return 1e6
    # Measure pricing error.
    return float(np.sqrt(np.mean((model - np.asarray(mids)) ** 2)))


# ---------------------------------------------------------------------------
# 0.3  Time changed stochastic time models, the last 12 models

#Now we first define PSI for everything, based on the definition provided
#This is the characteristic exponent
# %% Psi Vg
# Compute model return transform.
def psi_vg(u, C, G, M):
    u = np.asarray(u, dtype=complex)
    return C * (np.log(G * M) - np.log(G * M + (M - G) * 1j * u + u**2))


# %% Psi Cgmy
# Compute model return transform.
def psi_cgmy(u, C, G, M, Y):
    u = np.asarray(u, dtype=complex)
    gY = gamma_fn(-Y)
    return C * gY * ((M - 1j * u) ** Y - M**Y + (G + 1j * u) ** Y - G**Y)


# %% Psi Nig
# Compute model return transform.
def psi_nig(u, alpha, beta, delta):
    u = np.asarray(u, dtype=complex)
    return -delta * (np.sqrt(alpha**2 - (beta + 1j * u) ** 2) - np.sqrt(alpha**2 - beta**2))


# %% Psi Meixner
# Compute model return transform.
def psi_meixner(u, alpha, beta, delta):
    u = np.asarray(u, dtype=complex)
    return 2 * delta * (np.log(np.cos(beta / 2))
                        - np.log(np.cosh((alpha * u - 1j * beta) / 2)))


#Note in hindsight this GH parameterisation failed
#We use an already defined characteristic function
# %% Psi Gh
# Compute model return transform.
def psi_gh(u, alpha, beta, delta, nu):
    return gh_log_char(u, alpha, beta, delta, nu)


# The Levy exponents and their parameter names, for the time-changed models
# of Section 6. 
# %% Levy process registry
# Map each Levy model to its characteristic exponent and parameter names.
LEVY_PSI = {
    "VG": (psi_vg, ["C", "G", "M"]),
    "CGMY": (psi_cgmy, ["C", "G", "M", "Y"]),
    "NIG": (psi_nig, ["alpha", "beta", "delta"]),
    "Meixner": (psi_meixner, ["alpha", "beta", "delta"]),
    "GH": (psi_gh, ["alpha", "beta", "delta", "nu"]),
}


# ------------------------------------------------------------------ time changes
# the characteristic function of the
# integrated rate-of-time-change process.


#Now this is the time change models listed in the main text
# %% Varphi Cir
# Transform stochastic clock time.
def varphi_cir(u, t, kappa, eta, lam, y0=1.0):
    # Use complex frequencies.
    u = np.asarray(u, dtype=complex)
    gam = np.sqrt(kappa**2 - 2 * lam**2 * 1j * u)
    ekt = np.exp(gam * t)
    # Apply CIR transform formula.
    coth = (ekt + 1) / (ekt - 1)
    num = np.exp(kappa**2 * eta * t / lam**2) * np.exp(2 * y0 * 1j * u / (kappa + gam * coth))
    cosh_h = 0.5 * (np.exp(gam * t / 2) + np.exp(-gam * t / 2))
    sinh_h = 0.5 * (np.exp(gam * t / 2) - np.exp(-gam * t / 2))
    den = (cosh_h + kappa * sinh_h / gam) ** (2 * kappa * eta / lam**2)
    # Return clock transform.
    return num / den


# The two OU clocks. Both are integrals of a mean-reverting positive process
# driven by a subordinator, so the clock never runs backwards.
# %% Varphi Gamma Ou
# Transform stochastic clock time.
def varphi_gamma_ou(u, t, lam, a, b, y0=1.0):
    # Use complex frequencies.
    u = np.asarray(u, dtype=complex)
    e = 1 - np.exp(-lam * t)
    term1 = 1j * u * y0 * e / lam
    term2 = lam * a / (1j * u - lam * b) * (b * np.log(b / (b - 1j * u * e / lam)) - 1j * u * t)
    # Return clock transform.
    return np.exp(term1 + term2)


# %% Varphi Ig Ou
# Transform stochastic clock time.
def varphi_ig_ou(u, t, lam, a, b, y0=1.0):
    # Use complex frequencies.
    u = np.asarray(u, dtype=complex)
    kap = -2 * b**-2 * 1j * u / lam
    e = 1 - np.exp(-lam * t)
    s = np.sqrt(1 + kap * e)
    A = (1 - s) / kap + (1 / np.sqrt(1 + kap)) * (
        np.arctanh(s / np.sqrt(1 + kap)) - np.arctanh(1 / np.sqrt(1 + kap)))
    # Return clock transform.
    return np.exp(1j * u * y0 * e / lam + 2 * a * 1j * u / (b * lam) * A)


# The clocks and their parameter names.
# %% Stochastic clock registry
# Map each time-change model to its characteristic function and parameters.
TIME_CHANGE = {
    "CIR": (varphi_cir, ["kappa", "eta", "lam"]),
    "Gamma-OU": (varphi_gamma_ou, ["lam", "a", "b"]),
    "IG-OU": (varphi_ig_ou, ["lam", "a", "b"]),
}


# ------------------------------------------------------------------------ pricing
# %% Levy Sv Char Fn
# Combine process and clock transforms.
def levy_sv_char_fn(u, t, r, q, psi, levy_params, varphi, tc_params, S0):
    u = np.asarray(u, dtype=complex)
    num = varphi(-1j * psi(u, *levy_params), t, *tc_params)
    den = varphi(-1j * psi(-1j, *levy_params), t, *tc_params)
    return np.exp(1j * u * ((r - q) * t + np.log(S0))) * num / den ** (1j * u)


# The Carr-Madan pass for the time-changed models, structurally the same as
# the pure Levy one but taking the exponent and clock as arguments.
# %% Carr Madan Levy Sv
# Fourier-price option contracts.
def carr_madan_levy_sv(strikes, ttms, rates, divs, psi, levy_params,
                       varphi, tc_params, S0,
                       alpha=CM_ALPHA, n_grid=N_GRID, v_max=V_MAX):
    # Align contract arrays.
    strikes = np.asarray(strikes, dtype=float)
    ttms = np.asarray(ttms, dtype=float)
    rates = np.asarray(rates, dtype=float)
    divs = np.asarray(divs, dtype=float)

    v = np.linspace(1e-10, v_max, n_grid)[:, None]
    log_k = np.log(strikes)[None, :]
    prices = np.empty(len(strikes))
    denom = alpha**2 + alpha - v**2 + 1j * (2 * alpha + 1) * v

    # Price each maturity separately.
    for T in np.unique(ttms):
        sel = ttms == T
        r, q = rates[sel][0], divs[sel][0]
        cf = levy_sv_char_fn(v - (alpha + 1) * 1j, T, r, q,
                             psi, levy_params, varphi, tc_params, S0)
        integrand = np.real(np.exp(-1j * v * log_k[:, sel]) * np.exp(-r * T) * cf / denom)
        prices[sel] = np.exp(-alpha * log_k[0, sel]) / np.pi * np.trapezoid(integrand, v[:, 0], axis=0)

    # Collect contract prices.
    return prices


#This is the objective function but I add in the boundaries by each case as if statements
# %% Make Objective
# Build model fitting objective.
def make_objective(levy_name, tc_name, strikes, ttms, rates, divs, mids, S0):
    # Choose process and clock.
    psi, levy_names = LEVY_PSI[levy_name]
    varphi, tc_names = TIME_CHANGE[tc_name]
    n_levy = len(levy_names)
    mids = np.asarray(mids)

    # Build candidate score.
    def objective(params):
        # Split process and clock.
        lp, tp = params[:n_levy], params[n_levy:]
        # Reject inadmissible parameters.
        if levy_name in ("VG", "CGMY"):
            if lp[0] <= 1e-8 or lp[1] <= 1e-8 or lp[2] <= 1e-8:
                return 1e6
            if levy_name == "CGMY" and not (-1e-8 < lp[3] < 2):
                return 1e6
        elif levy_name == "NIG":
            if lp[0] <= 1e-8 or abs(lp[1]) >= lp[0] or lp[2] <= 1e-8:
                return 1e6
        elif levy_name == "Meixner":
            if lp[0] <= 1e-8 or lp[2] <= 1e-8 or abs(lp[1]) >= np.pi:
                return 1e6
        elif levy_name == "GH":
            if lp[0] <= 1e-8 or abs(lp[1]) >= lp[0] or lp[2] <= 1e-8:
                return 1e6
        if np.any(np.asarray(tp) <= 1e-8):
            return 1e6
        # Price candidate model.
        try:
            model = carr_madan_levy_sv(strikes, ttms, rates, divs,
                                       psi, tuple(lp), varphi, tuple(tp), S0)
        except Exception:
            return 1e6
        if not np.all(np.isfinite(model)) or np.any(model < 0):
            return 1e6
        # Measure pricing error.
        return float(np.sqrt(np.mean((model - mids) ** 2)))

    # Return score and labels.
    return objective, levy_names + tc_names


################# Data related activities - I've removed how I obtain the data cause its excessive
#I load it here, its available upon request or convert the relevant appendix to a csv

# The Korean risk-free rate and KOSPI 200 dividend yield
# %% Option-chain setup
# Extract observed prices and market inputs for subsequent fitting.
R, Q = 0.0291, 0.0079

# We save all these results to use later
# Both chains were loaded and validated before the analysis started.
K = opts["strike"].to_numpy()
T = opts["ttm"].to_numpy()
RATE = opts["rate"].to_numpy()
DIV = opts["div_yld"].to_numpy()
MID = opts["mid"].to_numpy()

# The seven expiries with their times to maturity, ordered from nearest to
# furthest. This fixes the column order of every per-maturity table.
MATS = [(d.strftime("%b %y"), float(g["ttm"].iloc[0]))
        for d, g in sorted(opts.groupby("expiry_date"),
                           key=lambda kv: kv[1]["ttm"].iloc[0])]




# The Black-Scholes price, needed here for the implied volatilities and again
# as the benchmark model of Section 2.

#Create the black scholes call price
# %% Bs Call
# Price Black-Scholes calls.
def bs_call(K, T, r, q, sigma, S0=S0):
    d1 = (np.log(S0 / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S0 * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

#Create the vega thats needed to compute volatility later on
# %% Bs Vega
# Measure price volatility sensitivity.
def bs_vega(K_, T_, r, q, sigma, spot):
    d1 = (np.log(spot / K_) + (r - q + 0.5 * sigma ** 2) * T_) / (sigma * np.sqrt(T_))
    return spot * np.exp(-q * T_) * np.sqrt(T_) * norm.pdf(d1)


#: Starting value for the per-contract Newton-Raphson iteration. 
# %% Implied-volatility settings
# Set the numerical seed used by implied-volatility inversion.
IV_SEED = 0.66

#: The same, for the S&P 500 chain of Section 9, whose volatility is a quarter
#: of the KOSPI's. This is Schoutens' own 0.20, which converges there.
SP_IV_SEED = 0.20

#Now calc implied volatility, I've added the newton raphson algo in there too
# %% Implied Vol
# Invert market option price.
def implied_vol(mkt, K_, T_, r, q, sigma0, spot, tol=1e-9, max_iter=100):
    sigma = sigma0
    # Solve for market volatility.
    for _ in range(max_iter):
        diff = bs_call(K_, T_, r, q, sigma, S0=spot) - mkt
        if abs(diff) < tol:
            return sigma
        v = bs_vega(K_, T_, r, q, sigma, spot)
        # Stop unstable iteration.
        if v < 1e-12 or sigma <= 0 or not np.isfinite(sigma):
            return np.nan
        sigma = sigma - diff / v
    return np.nan

#Now for the entire chain
# %% Chain Implied Vols
# Invert every contract price.
def chain_implied_vols(o, spot, sigma0=IV_SEED):
    return np.array([implied_vol(m, k_, t_, r_, q_, sigma0, spot)
                     for m, k_, t_, r_, q_ in zip(o["mid"], o["strike"],
                                                  o["ttm"], o["rate"],
                                                  o["div_yld"])])


#Convergence has succeeded
# %% Observed implied volatility
# Calculate market implied volatilities for the KOSPI option chain.
opts["iv"] = chain_implied_vols(opts, S0)
print(f"Implied volatility: {int(opts['iv'].notna().sum())}/{len(opts)} "
      f"contracts converged")
print(opts.groupby("expiry_date")["iv"]
      .agg(["count", "mean", "median", "min", "max"]).round(4).to_string())


#Create the four error measures
# %% Measures
# Summarize pricing errors.
def measures(mid, model):
    e = np.abs(mid - model)
    return dict(APE=100 * e.mean() / mid.mean(),
                AAE=float(e.mean()),
                RMSE=float(np.sqrt(np.mean((mid - model) ** 2))),
                ARPE=100 * float(np.mean(e / mid)))


# %% Black-Scholes calibration
# Fit and assess Black-Scholes implied volatility.
# 2. BLACK-SCHOLES

#Actually fit the black-scholes model - done via the newton raphson algorithm
# %% Fit Bs
# Fit common Black-Scholes volatility.
def fit_bs(o, spot=None, sigma0=IV_SEED, tol=1e-12, max_iter=100):

    # Set observed spot price.
    spot = S0 if spot is None else spot
    K_ = o["strike"].to_numpy()
    T_ = o["ttm"].to_numpy()
    r_ = o["rate"].to_numpy()
    q_ = o["div_yld"].to_numpy()
    mid = o["mid"].to_numpy()

    def g(s):
        p = bs_call(K_, T_, r_, q_, s, S0=spot)
        return float(np.mean((p - mid) * bs_vega(K_, T_, r_, q_, s, spot)))


    sigma, h = sigma0, 1e-6
    # Iterate volatility estimate.
    for _ in range(max_iter):
        gs = g(sigma)
        if abs(gs) < tol:
            break
        d = (g(sigma + h) - g(sigma - h)) / (2 * h)
        if d == 0 or not np.isfinite(d):
            break
        step = gs / d
        sigma -= step
        if sigma <= 0 or not np.isfinite(sigma):
            raise RuntimeError(f"Black-Scholes fit diverged from {sigma0:.4f}")
        if abs(step) < 1e-14:
            break
    # Return fitted volatility.
    return sigma


# One volatility fitted across all 212 contracts at once. This is the benchmark
# every later model is measured against.
# %% Black-Scholes results
# Fit pooled and per-maturity Black-Scholes models and report errors.
SIGMA_BS = fit_bs(opts)
bs_prices = bs_call(K, T, RATE, DIV, SIGMA_BS)
print(f"Black-Scholes, one sigma: {SIGMA_BS:.10f}")
print("  ", measures(MID, bs_prices))

# The same fit repeated expiry by expiry, giving seven volatilities rather than
# one. 
bs_per_mat, fitted = [], np.empty(len(opts))
for expiry, g in opts.groupby("expiry_date"):
    s = fit_bs(g)
    p = bs_call(g["strike"].to_numpy(), g["ttm"].to_numpy(),
                g["rate"].to_numpy(), g["div_yld"].to_numpy(), s)
    fitted[g.index.to_numpy()] = p
    bs_per_mat.append(dict(expiry=expiry.strftime("%b %y"), n=len(g),
                           ttm=float(g["ttm"].iloc[0]), sigma=s,
                           **measures(g["mid"].to_numpy(), p)))

# Ordered by maturity, this is the term structure reported in the results.
bs_per_mat = pd.DataFrame(bs_per_mat).sort_values("ttm")
print("\nBlack-Scholes per maturity:")
print(bs_per_mat.round(4).to_string(index=False))
print("  pooled:", measures(MID, fitted))

# %% Levy model calibration
# Fit the Levy option-pricing models to each option chain.
# 3. LEVY MODELS


#Now the levy models
# %% Meixner Density
# Evaluate Meixner return density.
def meixner_density(x, a, b, d, m):
    z = (x - m) / a
    log_c = 2 * d * np.log(2 * np.cos(b / 2)) - np.log(2 * a * np.pi) - gammaln(2 * d)
    return np.exp(np.clip(log_c + b * z + 2 * np.real(loggamma(d + 1j * z)),
                          -745, 700))

#This gets the meixner batch correctly, we manage to do this because it has the closed form density
#This one was harder, so took many attempts
#The others are more consistent cause I can use the Carr-Madan approach
# %% Meixner Batch
# Price Meixner option contracts.
def meixner_batch(K, T, r, q, a, b, d, S0_=None, n=1200):
    K = np.asarray(K, float); T = np.asarray(T, float)
    # Set martingale drift.
    m = r - q - 2 * d * (np.log(np.cos(b / 2)) - np.log(np.cos((a + b) / 2)))
    spot = S0 if S0_ is None else S0_
    lo = np.log(K / spot); hi = lo + 12 * a * np.sqrt(d * T) + 3
    t = np.linspace(0.0, 1.0, n)[None, :]
    # Grid future log-returns.
    x = lo[:, None] + (hi - lo)[:, None] * t
    dens = meixner_density(x, a, b, (d * T)[:, None], (m * T)[:, None])
    # Discount expected payoff.
    return np.exp(-r * T) * np.trapezoid((spot * np.exp(x) - K[:, None]) * dens,
                                         x, axis=1)


# Boundary conditions, enforced by returning a penalty 
# %% Ok Vg
# Check admissible model parameters.
def ok_vg(p):   return p[0] > 1e-8 and p[1] > 1e-8 and p[2] > 1.0
# %% Ok Cgmy
# Check admissible model parameters.
def ok_cgmy(p): return p[0] > 1e-8 and p[1] > 1e-8 and p[2] > 1.0 and p[3] < 2
# %% Ok Nig
# Check admissible model parameters.
def ok_nig(p):  return p[0] > 1e-8 and abs(p[1]) < p[0] and p[2] > 1e-8
# %% Ok Gh
# Check admissible model parameters.
def ok_gh(p):   return p[0] > 1e-8 and abs(p[1]) < p[0] and p[2] > 1e-8
# %% Ok Mx
# Check admissible model parameters.
def ok_mx(p):   return (p[0] > 1e-4 and p[2] > 1e-4 and abs(p[1]) < np.pi
                        and abs(p[0] + p[1]) < np.pi)


# Starting points
# %% Levy calibration settings
# Register Levy models, bounds, starting values, and validity checks.
LEVY = {
    "Meixner": dict(price=meixner_batch, ok=ok_mx, starts=[
        [0.10, -0.10, 1.00], [0.50, -1.00, 0.50], [0.20, 0.50, 2.00],
        [1.00, -2.00, 0.20], [0.05, -0.50, 3.00], [0.30, -1.50, 0.35],
        [0.80, 0.00, 1.00], [1.50, -1.00, 0.50], [2.00, -2.50, 0.30],
        [1.00, -0.50, 2.00]]),
    "VG": dict(price=carr_madan_batch_vg, ok=ok_vg, starts=[
        [1.5, 6.0, 15.0], [5.0, 20.0, 30.0], [0.5, 2.0, 5.0],
        [20.0, 40.0, 60.0], [1.0, 0.3, 1.6], [50.0, 90.0, 150.0]]),
    "CGMY": dict(price=carr_madan_batch, ok=ok_cgmy, starts=[
        [0.02, 0.08, 7.6, 1.29], [1.0, 5.0, 15.0, 0.5],
        [3.0, 60.0, 130.0, 1.36], [0.5, 2.0, 8.0, 1.0],
        [0.1, 1.0, 20.0, 1.5], [10.0, 30.0, 60.0, 0.2]]),
    "NIG": dict(price=carr_madan_batch_nig, ok=ok_nig, starts=[
        [6.2, -3.9, 0.16], [20.0, -5.0, 0.5], [2.0, -0.5, 0.3],
        [50.0, -20.0, 1.0], [100.0, 10.0, 50.0], [10.0, 0.0, 0.2]]),
    "GH": dict(price=carr_madan_batch_gh, ok=ok_gh, starts=[
        [3.8, -3.8, 0.24, -1.76], [10.0, -3.0, 0.5, -2.0],
        [36.5, 3.1, 18.8, -83.7], [5.0, 0.0, 1.0, -1.0],
        [20.0, -10.0, 2.0, -5.0], [2.0, -1.0, 0.3, 1.0]]),
}

#Now fit each levy model
# %% Fit Levy
# Find best Levy parameters.
def fit_levy(spec, o, spot=None, maxiter=4000):

    spot = S0 if spot is None else spot

    # Cache contract inputs.
    k, t = o["strike"].to_numpy(), o["ttm"].to_numpy()
    r, q, mid = (o["rate"].to_numpy(), o["div_yld"].to_numpy(),
                 o["mid"].to_numpy())

    # Score candidate parameters.
    def obj(p):
        # Reject invalid parameters.
        if not spec["ok"](p):
            return 1e6
        # Price candidate model.
        try:
            m = spec["price"](k, t, r, q, *p, spot)
        except Exception:
            return 1e6
        if not np.all(np.isfinite(m)):
            return 1e6
        # Measure pricing error.
        return float(np.sqrt(np.mean((m - mid) ** 2)))

    best = None
    # Try multiple initial values.
    for x0 in spec["starts"]:
        res = minimize(obj, x0=np.array(x0, float), method="Nelder-Mead",
                       options={"xatol": 1e-6, "fatol": 1e-6,
                                "maxiter": maxiter, "maxfev": maxiter})
        if res.fun < 1e5 and (best is None or res.fun < best.fun):
            best = res
    return best


# %% Levy calibration results
# Fit each Levy model to the full chain and report errors.
print("\nLevy models across the chain:")
# The five whole-chain fits. Each parameter vector is kept, since Section 4
# reuses it as the leading starting point for the per-maturity calibrations.
levy_fits = {}
for name, spec in LEVY.items():
    best = fit_levy(spec, opts)
    levy_fits[name] = best.x
    p = spec["price"](K, T, RATE, DIV, *best.x, S0)
    print(f"  {name:<8} {np.round(best.x, 4)}  {measures(MID, p)}")

# %% Log-return densities
# Recover risk-neutral return densities from fitted Levy models.
# 3b. RECOVERED LOG-RETURN DENSITIES
# density of log(S_T/S_0) under each Levy fit,
# recovered from the characteristic function. 

#Get the drift parameter for the respective levy model
# %% Levy Drift
# Set risk-neutral Levy drift.
def levy_drift(name, params):
    if name == "Meixner":
        a, b, d = params
        return r_ - q_ - 2 * d * (np.log(np.cos(b / 2))
                                  - np.log(np.cos((a + b) / 2)))
    return {"VG": m_new_vg, "CGMY": m_new_cgmy, "NIG": m_new_nig,
            "GH": m_new_gh}[name](*params, r_, q_)

#Get the respective log return density, by fourier inversion
# %% Logreturn Pdf
# Invert fitted return transform.
def logreturn_pdf(x, T_, psi, params, drift, n_u=2 ** 15):
    # Create Fourier frequency grid.
    u = np.linspace(0.0, 60.0 / (SIGMA_BS * np.sqrt(T_)), n_u)
    cf = np.exp(T_ * psi(u, *params) + 1j * u * drift * T_)
    bad = ~np.isfinite(cf)
    if bad.any():
        cut = int(np.argmax(bad))
        u, cf = u[:cut], cf[:cut]
    integ = np.real(np.exp(-1j * u[None, :] * np.asarray(x)[:, None]) * cf)
    # Invert characteristic function.
    return np.trapezoid(integ, u, axis=1) / np.pi

#Now get the moments
# %% Density Moments
# Summarize fitted return density.
def density_moments(T_, name, params):

    # Set risk-neutral drift.
    drift = levy_drift(name, params)
    centre = (r_ - q_ - 0.5 * SIGMA_BS ** 2) * T_
    half = 6 * SIGMA_BS * np.sqrt(T_)
    x = np.linspace(centre - half, centre + half, 1500)

    # Use closed-form density.
    if name == "Meixner":
        a, b, d = params
        f = meixner_density(x, a, b, d * T_, drift * T_)
    else:
        f = logreturn_pdf(x, T_, LEVY_PSI[name][0], params, drift)

    # Integrate density moments.
    mass = np.trapezoid(f, x)
    mu = np.trapezoid(x * f, x) / mass
    c2, c3, c4 = (np.trapezoid((x - mu) ** k * f, x) / mass for k in (2, 3, 4))
    return dict(mass=mass, mean=mu, sd=np.sqrt(c2),
                skew=c3 / c2 ** 1.5, exkurt=c4 / c2 ** 2 - 3.0)


# %% Recovered density results
# Calculate and report return-density summaries for fitted models.
print("\nRecovered log-return densities, front month and longest maturity:")
# The two maturities the density figures are drawn at. 
r_, q_ = R, Q
dens_rows = [dict(expiry=lab, model=name,
                  **density_moments(t_, name, tuple(params)))
             for lab, t_ in (MATS[0], MATS[-1])
             for name, params in levy_fits.items()]
print(pd.DataFrame(dens_rows).round(6).to_string(index=False))

# %% Per-maturity calibration
# Refit Black-Scholes and Levy models separately for each expiry.
# 4. THE LEVY MODELS, FITTED MATURITY BY MATURITY
# Each model is refitted to the contracts of one expiry at a time. 

print("\nPer-maturity calibrations (RMSE):")
# Black-Scholes and all five Levy models, refitted to each expiry in turn.
per_mat_rows = []

#Now go through expiry in a for loop for efficiency
for expiry, g in sorted(opts.groupby("expiry_date"),
                        key=lambda kv: kv[1]["ttm"].iloc[0]):
    lab = expiry.strftime("%b %y")
    s = fit_bs(g)
    p = bs_call(g["strike"].to_numpy(), g["ttm"].to_numpy(),
                g["rate"].to_numpy(), g["div_yld"].to_numpy(), s)
    per_mat_rows.append(dict(model="Black-Scholes", expiry=lab, n=len(g),
                             params=f"sigma={s:.4f}",
                             **measures(g["mid"].to_numpy(), p)))

    # Fit each Levy family.
    for name, spec in LEVY.items():
        sub = dict(spec)
        sub["starts"] = [list(levy_fits[name])] + spec["starts"][:3]

        # Fit current maturity.
        best = fit_levy(sub, g, maxiter=1500)
        if best is None:
            continue
        m = spec["price"](g["strike"].to_numpy(), g["ttm"].to_numpy(),
                          g["rate"].to_numpy(), g["div_yld"].to_numpy(),
                          *best.x, S0)
        per_mat_rows.append(dict(model=name, expiry=lab, n=len(g),
                                 params=", ".join(f"{v:.4f}" for v in best.x),
                                 **measures(g["mid"].to_numpy(), m)))

# RMSE by model and expiry: the per-maturity table of the results.
per_mat = pd.DataFrame(per_mat_rows)
print(per_mat.pivot(index="model", columns="expiry", values="RMSE")
      .reindex(["Black-Scholes"] + list(LEVY))[[m for m, _ in MATS]]
      .round(4).to_string())

# %% BNS calibration
# Fit the Barndorff-Nielsen-Shephard option-pricing models.
# 5. BNS

BNS_STARTS = {
    "Gamma-OU": [(-1.2606, 0.5783, 1.4338, 11.6641, 0.01450),
                 (-1.0, 1.0, 1.5, 10.0, 0.05), (-2.0, 2.0, 1.0, 5.0, 0.20),
                 (-0.5, 5.0, 2.0, 20.0, 0.40), (-5.0, 8.0, 3.0, 30.0, 0.65),
                 (-0.2, 0.5, 0.5, 2.0, 0.70), (-10.0, 10.0, 5.0, 50.0, 0.80),
                 (-1.0, 3.0, 0.3, 1.0, 0.30)],
    "IG-OU": [(-0.1926, 0.0636, 6.2410, 0.7995, 0.01560),
              (-0.5, 1.0, 3.0, 1.0, 0.05), (-1.0, 3.0, 1.0, 2.0, 0.30),
              (-0.3, 8.0, 0.1, 2.0, 0.85), (-2.0, 5.0, 0.5, 1.5, 0.50),
              (-0.1, 0.5, 5.0, 0.8, 0.20), (-3.0, 10.0, 0.05, 3.0, 0.75),
              (-0.7, 2.0, 2.0, 0.5, 0.40)],
}
# Each model paired with its objective and its pricer.
BNS_MODELS = {"Gamma-OU": (rmse_objective_bns, carr_madan_batch_bns),
              "IG-OU": (rmse_objective_ig, carr_madan_batch_ig)}

print("\nBNS models:")
# Both models fitted from all eight starts.
bns_fits, bns_starts_rows = {}, []

#Go through each specific model in BNS models - note we called the function in that term
for name, (obj, pricer) in BNS_MODELS.items():
    best = None

    # Compare candidate starts.
    for i, x0 in enumerate(BNS_STARTS[name], 1):
        res = minimize(obj, x0=np.array(x0, float),
                       args=(K, T, RATE, DIV, MID, S0), method="Nelder-Mead",
                       options={"xatol": 1e-6, "fatol": 1e-6,
                                "maxiter": 4000, "maxfev": 4000})

        # Add candidate starts.
        bns_starts_rows.append(dict(model=name, start=i,
                                    **dict(zip(["rho", "lam", "a", "b", "s0"],
                                               res.x)), RMSE=res.fun))

        # Keep lowest error.
        if best is None or res.fun < best.fun:
            best = res

    # Save fitted parameters.
    bns_fits[name] = best.x
    p = pricer(K, T, RATE, DIV, *best.x, S0)
    print(f"  BNS {name:<9} {np.round(best.x, 4)}  {measures(MID, p)}")

# The full set of terminal vectors, showing how many starts agree on the
# optimum and how far the rest drift from it.
print("\n  terminal values from every start:")
print(pd.DataFrame(bns_starts_rows).round(4).to_string(index=False))




# %% Stochastic time change
# Calibrate Levy processes under stochastic volatility clocks.
# 6. STOCHASTIC TIME CHANGE
# 
# The twelve combinations of four Levy processes with three clocks.
MEIXNER_STARTS = [
    [0.1231, -0.5875, 3.3588], [0.1108, -0.9858, 3.6288],
    [0.0890, -1.1323, 5.0262], [0.3, -0.5, 1.5],
    [0.05, -1.5, 8.0], [0.2, -0.8, 2.5],
    [0.15, -2.0, 4.0], [0.5, -0.3, 1.0],
]
VG_STARTS = [
    [11.9896, 25.8523, 35.5344], [11.4838, 23.2880, 40.1291],
    [14.9248, 26.1529, 50.4425], [5.0, 10.0, 20.0],
    [20.0, 40.0, 60.0], [1.0, 5.0, 10.0],
    [8.0, 15.0, 30.0], [30.0, 50.0, 80.0],
]
CGMY_STARTS = [
    [0.0074, 0.1025, 11.3940, 1.6765], [0.0415, 3.9134, 30.6322, 1.3664],
    [0.0672, 6.1316, 44.7448, 1.2911], [0.5, 5.0, 15.0, 0.5],
    [0.01, 1.0, 5.0, 1.0], [0.1, 2.0, 20.0, 1.5],
    [0.005, 0.5, 8.0, 1.8], [0.2, 8.0, 35.0, 0.8],
]
NIG_STARTS = [
    [18.4815, -4.8412, 0.4685], [29.4722, -15.9048, 0.5071],
    [29.1553, -13.9331, 0.5600], [10.0, -2.0, 1.0],
    [40.0, -20.0, 0.3], [15.0, -8.0, 0.7],
    [50.0, -25.0, 0.4], [8.0, -1.0, 1.5],
]

# Clock starting points, shared across the Levy families.
TC_STARTS = {
    "CIR": [[0.5391, 1.5746, 1.8772], [0.5145, 0.9029, 1.3750],
            [0.6020, 1.5560, 1.9992], [0.3881, 1.4012, 1.3612],
            [0.6, 1.5, 1.0], [1.0, 1.0, 1.0],
            [0.4, 1.4, 1.36], [1.5, 0.8, 2.5]],
    "Gamma-OU": [[0.6252, 0.4239, 0.5962], [1.2517, 0.5841, 0.6282],
                 [0.8826, 0.5945, 0.8524], [1.0740, 0.3573, 0.6143],
                 [1.1729, 0.5914, 0.6558], [1.0, 1.0, 1.0],
                 [0.5, 0.3, 0.4], [2.0, 0.8, 1.2]],
    "IG-OU": [[1.1559, 0.6496, 0.8572], [1.2801, 0.6615, 0.8104],
              [1.0622, 0.6092, 0.9999], [1.2190, 0.6564, 0.8266],
              [1.1315, 0.8993, 0.6168], [1.0, 1.0, 1.0],
              [0.6, 0.4, 0.5], [2.0, 1.0, 1.5]],
}

# The starting points by Levy process, so the loop below can pair each
# with every clock.
SV_STARTS = {"Meixner": MEIXNER_STARTS, "VG": VG_STARTS,
             "CGMY": CGMY_STARTS, "NIG": NIG_STARTS}

# All eight starts of each list are used
N_SV_STARTS = 8

#Now calibrate the stochastic volatility models
# %% Calibrate Sv
# Fit stochastic-volatility combinations.
def calibrate_sv(chain_tag, o, spot, levy_name, tc_name, levy_starts,
                 n_starts=N_SV_STARTS, maxiter=3000):

    # Extract contract inputs.
    k = o["strike"].to_numpy()
    t_ = o["ttm"].to_numpy()
    r = o["rate"].to_numpy()
    q = o["div_yld"].to_numpy()
    mid = o["mid"].to_numpy()

    # Build pricing objective.
    objective, pnames = make_objective(levy_name, tc_name, k, t_, r, q, mid, spot)

    # Pair process and clock starts.
    starts = [lp + tp for lp, tp
              in zip(levy_starts, TC_STARTS[tc_name])][:n_starts]

    t0 = time.time()

    # Fit every starting point.
    results = [minimize(objective, x0=np.array(x0, dtype=float),
                        method="Nelder-Mead",
                        options={"xatol": 1e-5, "fatol": 1e-5,
                                 "maxiter": maxiter, "maxfev": maxiter})
               for x0 in starts]

    # Keep best fit.
    results.sort(key=lambda res: res.fun)
    best = results[0]

    # Count similar solutions.
    n_agree = sum(1 for res in results if res.fun < best.fun * 1.01)

    # Reprice fitted contracts.
    psi, _ = LEVY_PSI[levy_name]
    varphi, _ = TIME_CHANGE[tc_name]
    n_levy = len(LEVY_PSI[levy_name][1])
    lp, tp = tuple(best.x[:n_levy]), tuple(best.x[n_levy:])
    model = carr_madan_levy_sv(k, t_, r, q, psi, lp, varphi, tp, spot)

    # Report fit diagnostics.
    stats = dict(chain=chain_tag, levy=levy_name, time_change=tc_name,
                 n_contracts=len(o), n_params=len(best.x),
                 **measures(mid, model),
                 n_agree=n_agree, n_starts=len(starts),
                 seconds=time.time() - t0)
    stats["RMSE"] = best.fun
    stats.update(dict(zip(pnames, best.x)))
    return stats


# Every Levy process against every clock: four times three fits.
#Now do it ALL
# %% Stochastic-volatility results
# Fit the Levy and stochastic-clock combinations.
sv_rows = []
for levy_name, starts in SV_STARTS.items():
    for clock in ("CIR", "Gamma-OU", "IG-OU"):
        stats = calibrate_sv("k200", opts, S0, levy_name, clock, starts)
        sv_rows.append(stats)
        print(f"  {levy_name}-{clock}: RMSE {stats['RMSE']:.4f}")

# Parameters and error measures for all twelve, the goodness-of-fit table.
sv = pd.DataFrame(sv_rows)

# %% Stochastic-volatility moments
# Compute moments implied by the fitted stochastic-volatility models.
# 7. MOMENTS OF THE STOCHASTIC VOLATILITY FITS
# Variance and excess kurtosis of the risk-neutral log return, read off the
# characteristic function used for pricing. 

#Testing Ladder
H_LADDER = [3e-3, 5e-3, 1e-2, 2e-2, 3e-2, 5e-2, 8e-2, 1.2e-1]

#Tolerance
TOL = 0.02

#Define the cumulants 
# %% Cumulants
# Approximate second and fourth cumulants.
def cumulants(T_, cf, h):
    K0 = 0.0 + 0.0j
    k2 = -np.real((cf(h) - 2 * K0 + cf(-h)) / h ** 2)
    k4 = np.real((cf(2 * h) - 4 * cf(h) + 6 * K0
                  - 4 * cf(-h) + cf(-2 * h)) / h ** 4)
    return k2, k4

#Now define the actual moments for the stochastic volatility models using those cumulants
# %% Sv Moments
# Estimate model volatility moments.
def sv_moments(T_, levy_name, clock, lp, tp):

    # Select fitted transforms.
    psi, _ = LEVY_PSI[levy_name]
    varphi, _ = TIME_CHANGE[clock]

    # Center log-return transform.
    def logphi(u):
        v = levy_sv_char_fn(np.array([u], dtype=complex), T_, R, Q,
                            psi, lp, varphi, tp, S0)[0]
        return np.log(v * np.exp(-1j * u * np.log(S0)))

    est = []
    # Compare numerical step sizes.
    for h in H_LADDER:
        try:
            k2, k4 = cumulants(T_, logphi, h)
        except Exception:
            continue
        if k2 > 0:
            est.append((np.sqrt(k2), k4 / k2 ** 2))

    # Require stable estimates.
    def settle(i):
        for j in range(len(est) - 1):
            a, b = est[j][i], est[j + 1][i]
            if abs(a - b) <= TOL * max(1.0, abs(a)):
                return a
        return np.nan

    # Keep stable moment estimates.
    return settle(0), settle(1)


# Both moments for all twelve models at all seven maturities.
# %% Stochastic-volatility moment results
# Compute and report the fitted risk-neutral moments.
mom_rows = []
for _, r in sv.iterrows():
    levy_name, clock = r["levy"], r["time_change"]
    lp = [r[c] for c in LEVY_PSI[levy_name][1]]
    tp = [r[c] for c in TIME_CHANGE[clock][1]]
    for lab, t_ in MATS:
        sd, ek = sv_moments(t_, levy_name, clock, lp, tp)
        mom_rows.append(dict(model=f"{levy_name}-{clock}", expiry=lab,
                             ttm=t_, sd=sd, exkurt=ek, rmse=r["RMSE"]))

# Excess kurtosis by maturity, the kurtosis table of the results.
moments = pd.DataFrame(mom_rows)
print(moments.pivot(index="expiry", columns="model", values="exkurt")
      .reindex([m for m, _ in MATS]).round(3).to_string())

# %% Implied-volatility term structure
# Compare implied volatility and model moments across maturities.
# 8. IMPLIED VOLATILITY TERM STRUCTURE

#Define volatility moments that we need
vol = moments.assign(vol=lambda d: d["sd"] / np.sqrt(d["ttm"]))

#Print
print(vol.pivot(index="expiry", columns="model", values="vol")
      .reindex([m for m, _ in MATS]).round(4).to_string())

#Now actually get the levy unit moments
# %% Levy Unit Moments
# Compute unit-time Levy moments.
def levy_unit_moments(name, p):
    # Select Levy family.
    if name == "Meixner":
        a, b, d = p
        return a * d * np.tan(b / 2), a ** 2 * d / (2 * np.cos(b / 2) ** 2)
    if name == "VG":
        C, G, M = p
        return C * (G - M) / (M * G), C * (G ** 2 + M ** 2) / (M * G) ** 2
    if name == "NIG":
        a, b, d = p
        return (d * b / np.sqrt(a ** 2 - b ** 2),
                a ** 2 * d * (a ** 2 - b ** 2) ** -1.5)
    # Check finite variance.
    if name == "CGMY":
        C, G, M, Y = p
        if Y >= 2:
            return np.nan, np.nan
        return (C * (M ** (Y - 1) - G ** (Y - 1)) * gamma_fn(1 - Y),
                C * (M ** (Y - 2) + G ** (Y - 2)) * gamma_fn(2 - Y))
    raise ValueError(name)

#Find two ends
# %% Term-structure results
# Report short- and long-maturity volatility properties.
print("\nShort- and long-maturity limits:")
for _, r in sv.iterrows():
    levy_name, clock = r["levy"], r["time_change"]
    EX, VX = levy_unit_moments(levy_name, [r[c] for c in LEVY_PSI[levy_name][1]])
    if not np.isfinite(VX):
        print(f"  {levy_name}-{clock}: variance not finite")
        continue
    # Match clock parameterizations.
    if clock == "CIR":
        k, eta, lam = r["kappa"], r["eta"], r["lam"]
        ratio = eta * (1 + (EX ** 2 / VX) * lam ** 2 / k ** 2)
        rate = k
    else:
        lam, a, b = r["lam"], r["a"], r["b"]
        power = 2 if clock == "Gamma-OU" else 3
        ratio = a / b + (EX ** 2 / VX) * (2 * a / (lam * b ** power))
        rate = lam
    print(f"  {levy_name}-{clock:<9} sigma(0) {np.sqrt(VX):.4f}  "
          f"sigma(inf) {np.sqrt(VX * ratio):.4f}  "
          f"half-life {365 * np.log(2) / rate:.1f} days")

# %% Validation
# Apply the pricing routines to the separate validation dataset.
# 9. VALIDATION 
#This was all about comparing to schoutens data

# The same columns as the KOSPI chain, so every routine below is called
# unchanged - using the functions we already defined
spK, spT = sp["strike"].to_numpy(), sp["ttm"].to_numpy()
spR, spQ = sp["rate"].to_numpy(), sp["div_yld"].to_numpy()
spMID = sp["mid"].to_numpy()

# Black-Scholes.
sp_sigma = fit_bs(sp, SP_S0, sigma0=SP_IV_SEED)
sp_bs = bs_call(spK, spT, spR, spQ, sp_sigma, S0=SP_S0)
print(f"\nS&P 500 Black-Scholes: sigma = {sp_sigma:.4f}")
print("  ", measures(spMID, sp_bs))

# Levy models. The starting points are Schoutens' Table 6.1 estimates, since
# the object here is to recover his optimum rather than to search widely.
SP500_LEVY_STARTS = {
    "Meixner": [0.3977, -1.4940, 0.3462],
    "VG": [1.3, 6.0, 15.0],
    "CGMY": [0.0244, 0.0765, 7.5515, 1.2945],
    "NIG": [6.1882, -3.8941, 0.1622],
    "GH": [1.0, -5.0, 0.5, -5.0],
}

# The five Levy models, fitted from Schoutens' own estimate plus three of the
# dispersed starts as a check that his optimum is the better one.
print("\nS&P 500 Levy models:")
sp_levy_fits = {}
for name, spec in LEVY.items():
    sub = dict(spec)
    sub["starts"] = [SP500_LEVY_STARTS[name]] + spec["starts"][:3]
    best = fit_levy(sub, sp, SP_S0)
    if best is None:
        print(f"  {name:<8} no admissible fit")
        continue
    sp_levy_fits[name] = best.x
    p = spec["price"](spK, spT, spR, spQ, *best.x, SP_S0)
    print(f"  {name:<8} {np.round(best.x, 4)}  {measures(spMID, p)}")

# BNS, from the same starting points as Section 5.
print("\nS&P 500 BNS models:")
for name, (obj, pricer) in BNS_MODELS.items():
    best = None
    for x0 in BNS_STARTS[name]:
        res = minimize(obj, x0=np.array(x0, float),
                       args=(spK, spT, spR, spQ, spMID, SP_S0),
                       method="Nelder-Mead",
                       options={"xatol": 1e-6, "fatol": 1e-6,
                                "maxiter": 4000, "maxfev": 4000})
        if best is None or res.fun < best.fun:
            best = res
    p = pricer(spK, spT, spR, spQ, *best.x, SP_S0)
    print(f"  BNS {name:<9} {np.round(best.x, 4)}  {measures(spMID, p)}")

# The twelve time-changed models, through the same runner as Section 6.
print("\nS&P 500 stochastic time-change models:")
for levy_name, starts in SV_STARTS.items():
    for clock in ("CIR", "Gamma-OU", "IG-OU"):
        stats = calibrate_sv("sp500", sp, SP_S0, levy_name, clock, starts)
        print(f"  {levy_name}-{clock}: RMSE {stats['RMSE']:.4f}")
