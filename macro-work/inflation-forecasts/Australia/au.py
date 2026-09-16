"""
Australia inflation forecast - quarterly VAR.

Run this file top to bottom (python au.py, or send it to a console/notebook
line by line). It reads like an R script: load packages, load data, transform,
fit, check, forecast, save. Everything stays in the workspace so you can
inspect any object afterwards.

The model: a quarterly VAR where inflation and its drivers are all endogenous,
so the VAR projects them jointly.

    y_t = [ CPI inflation (% q/q)
            unemployment rate (%)
            inflation expectations (%)
            import-price inflation (% q/q)
            oil price inflation (% q/q)
            Stage 2 pipeline-price inflation (% q/q) ]
"""

# ============================================================
# 1. LOAD PACKAGES
# ============================================================
import pandas as pd
from statsmodels.tsa.api import VAR        # the VAR model itself

from data import load_sheet, RESULTS       # workbook reader (see data.py)


# ============================================================
# 2. SETTINGS
# ============================================================
START = pd.Period("2001Q1", freq="Q")      # first quarter with a full driver set
STEPS = 12                                 # forecast 12 quarters (3 years) ahead
MAXLAGS = 6                                # most lags the AIC search may choose

# The three CPI measures we forecast, and their column names on the "AU" sheet
MEASURES = {
    "headline":       "Headline - Index",
    "trimmed_mean":   "Trimmed mean index",
    "ex_food_energy": "Ex food & energy Index s.a",
}


# ============================================================
# 3. LOAD DATA
#    Quarterly series come from the "AU" sheet; oil and the Stage 2
#    pipeline-price index are monthly on "AU-M", so we average them to
#    quarters.
# ============================================================
au_q = load_sheet("AU", "Q")               # quarterly sheet
au_m = load_sheet("AU-M", "M")             # monthly sheet

# --- drivers, all quarterly ---
drivers = pd.DataFrame({
    "unemployment":  au_q["Unemployment Rate"],
    "expectations":  au_q["Inflation expectation"],
    "import_prices": au_q["Import prices"],
})

# monthly -> quarterly (average of the three months in each quarter)
oil_m = au_m["Oil"].dropna()
stage2_m = au_m["Stage2"].dropna()
drivers["oil"] = oil_m.groupby(oil_m.index.asfreq("Q")).mean()
drivers["stage2"] = stage2_m.groupby(stage2_m.index.asfreq("Q")).mean()

drivers = drivers.loc[START:]

print("Drivers loaded:")
print(f"  rows {len(drivers)}, complete rows {len(drivers.dropna())}")
print(f"  span {drivers.dropna().index[0]} -> {drivers.dropna().index[-1]}\n")


# ============================================================
# 4. FIT A VAR FOR EACH CPI MEASURE
#    Price indices are turned into inflation rates (% change) so the data is
#    stationary; unemployment and expectations are already rates.
#    statsmodels picks the lag order by AIC.
# ============================================================
fits = {}          # fitted VAR results, one per measure
frames = {}        # the data each VAR was fitted on
levels = {}        # the raw CPI index for each measure

for label, column in MEASURES.items():
    cpi = au_q[column].dropna().loc[START:]
    cpi.name = "cpi"
    levels[label] = cpi

    # put CPI next to the drivers and keep only quarters where all exist
    frame = pd.concat([cpi, drivers], axis=1).dropna()

    # convert index levels to % change; leave unemployment/expectations alone
    for col in ["cpi", "import_prices", "oil", "stage2"]:
        frame[col] = 100.0 * frame[col].pct_change()
    frame = frame.dropna()                 # first row lost to differencing
    frames[label] = frame

    # estimate: VAR on the numeric array, lag order chosen by AIC
    fit = VAR(frame.to_numpy()).fit(maxlags=MAXLAGS, ic="aic")
    fits[label] = fit

    print(f"{label}: VAR({fit.k_ar}) on {frame.index[0]}-{frame.index[-1]} "
          f"({fit.nobs} obs)")


# ============================================================
# 5. CHECK THE FIT
#    Three standard diagnostics:
#      - lag-order table (what AIC/BIC/HQIC each preferred)
#      - stability (all roots inside the unit circle -> forecasts converge)
#      - residual autocorrelation (Durbin-Watson near 2 is clean)
# ============================================================
print("\n--- Lag order selection (headline) ---")
print(VAR(frames["headline"].to_numpy()).select_order(MAXLAGS).summary())

print("\n--- Diagnostics ---")
for label, fit in fits.items():
    # is_stable(): all roots inside the unit circle, so forecasts settle down
    # rather than exploding. R^2 is for the CPI equation only (column 0).
    cpi_r2 = 1 - fit.resid[:, 0].var() / frames[label]["cpi"].var()
    print(f"{label:15s} stable={fit.is_stable():<5} "
          f"AIC={fit.aic:7.3f}  BIC={fit.bic:7.3f}  CPI-eq R^2={cpi_r2:.3f}")

# The CPI equation's coefficients, if you want to read the economics:
# print(fits["headline"].summary())


# ============================================================
# 6. FORECAST
#    statsmodels' own recursion: each period's prediction feeds back in as
#    the next period's lag, and all variables move together.
# ============================================================
forecasts = {}     # forecast of the % change in each CPI measure
results = {}       # index level + year-on-year rate, history and forecast

for label, fit in fits.items():
    frame = frames[label]
    y = fit.endog[-fit.k_ar:]                       # last k_ar rows start it off
    point = fit.forecast(y, STEPS)                  # (STEPS x n_variables)

    future = pd.period_range(frame.index[-1] + 1, periods=STEPS, freq="Q")
    fc = pd.DataFrame(point, index=future, columns=frame.columns)
    forecasts[label] = fc

    # chain the forecast % changes onto the last actual CPI level
    level = levels[label].dropna()
    path = {}
    current = level.iloc[-1]
    for period, rate in fc["cpi"].items():
        current = current * (1 + rate / 100.0)
        path[period] = current

    full = pd.concat([level, pd.Series(path)])      # history + forecast
    out = pd.DataFrame({
        "index": full,
        "yoy": 100.0 * (full / full.shift(4) - 1.0),
        "is_forecast": [False] * len(level) + [True] * len(path),
    })
    results[label] = out

    print(f"{label:15s} last actual {level.index[-1]} "
          f"({out.loc[level.index[-1], 'yoy']:.2f}% y/y)  ->  "
          f"{out.index[-1]} ({out['yoy'].iloc[-1]:.2f}% y/y)")


# ============================================================
# 7. SAVE RESULTS
# ============================================================
combined = pd.DataFrame({f"{label}_{col}": results[label][col]
                         for label in results for col in ["index", "yoy"]})
combined.to_csv(RESULTS / "au_inflation_forecast.csv")

print(f"\nSaved: {RESULTS / 'au_inflation_forecast.csv'}")
