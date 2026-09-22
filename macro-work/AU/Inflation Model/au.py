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
            oil price level (USD per barrel)
            Stage 2 pipeline-price inflation (% q/q) ]
"""

# %% Imports and data access
# Load pandas, the VAR estimator, and the local workbook reader.
import pandas as pd
from statsmodels.tsa.api import VAR        # the VAR model itself

from data import load_sheet, RESULTS       # workbook reader (see data.py)


# %% Forecast settings
# Set the starting quarter, horizon, maximum lag order, and CPI measures.
START = pd.Period("2001Q1", freq="Q")      # first quarter with a full driver set
STEPS = 12                                 # forecast 12 quarters (3 years) ahead
MAXLAGS = 6                                # most lags the AIC search may choose

# The three CPI measures we forecast, and their column names on the "AU" sheet
MEASURES = {
    "headline":       "Headline - Index",
    "trimmed_mean":   "Trimmed mean index",
    "ex_food_energy": "Ex food & energy Index s.a",
}


# %% Input data and quarterly drivers
# Read AU quarterly series and average monthly oil and Stage 2 by quarter.
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


# %% Fit the three CPI models
# Convert price indices to quarterly changes and select each VAR lag by AIC.
fits = {}          # fitted VAR results, one per measure
frames = {}        # the data each VAR was fitted on
levels = {}        # the raw CPI index for each measure

for label, column in MEASURES.items():
    cpi = au_q[column].dropna().loc[START:]
    cpi.name = "cpi"
    levels[label] = cpi

    # put CPI next to the drivers and keep only quarters where all exist
    frame = pd.concat([cpi, drivers], axis=1).dropna()

    # Convert CPI and other price indices to changes; keep oil, unemployment and expectations in levels.
    for col in ["cpi", "import_prices",  "stage2"]:
        frame[col] = 100.0 * frame[col].pct_change()

    frame = frame.dropna()                 # first row lost to differencing
    frames[label] = frame

    # estimate: VAR on the numeric array, lag order chosen by AIC
    fit = VAR(frame.to_numpy()).fit(maxlags=MAXLAGS, ic="aic")
    fits[label] = fit

    print(f"{label}: VAR({fit.k_ar}) on {frame.index[0]}-{frame.index[-1]} "
          f"({fit.nobs} obs)")


# %% Fit diagnostics
# Print lag-order criteria, stability, and a CPI-equation fit summary.
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


# %% Dynamic forecasts and year-ended rates
# Project each VAR, chain CPI changes onto the last index, and calculate YoY rates.
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


# %% Save forecast results
# Write the combined historical and projected index levels and YoY rates.
combined = pd.DataFrame({f"{label}_{col}": results[label][col]
                         for label in results for col in ["index", "yoy"]})
combined.to_csv(RESULTS / "au_inflation_forecast.csv")

print(f"\nSaved: {RESULTS / 'au_inflation_forecast.csv'}")
