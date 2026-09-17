"""Korea inflation forecast - VAR models for CPI and PPI.

Data: `Data Inputs.xlsx`, sheet "KR" (monthly: CPI measures, PPI, oil,
unemployment, inflation expectations, import prices, Stage 2).

Model
-----
Monthly VARs, all variables endogenous:

  CPI models   y_t = [ CPI inflation (% m/m)
                       inflation expectations (%)
                       oil price inflation (% m/m)
                       import-price inflation (% m/m)
                       unemployment rate (%) ]

  PPI model    the same driver block with PPI inflation as the target.

statsmodels VAR, lag order by AIC, dynamic multi-step forecasts.
Headline CPI, core CPI (ex food & energy) and PPI each get their own VAR.
"""
# %% Imports and data access
# Load pandas and the local workbook and VAR helpers.
import pandas as pd

from data import build_frame, pct_change, series, RESULTS
from varmodel import fit_var, forecast, report

# %% Model configuration
# Define CPI and PPI targets, shared drivers, sample, and horizon.
CPI_MEASURES = {
    "headline": "KR CPI",
    "core": "KR Core CPI (Excl Food & Energy)",
}
PPI_MEASURES = {"ppi": "KR PPI"}

DRIVERS = {
    "expectations": ("KR", "KR Inflation Expectation"),
    "oil": ("KR", "WTI Oil Mthly Average"),
    "import_prices": ("KR", "KR ImPI"),
    "unemployment": ("KR", "KR Unemployment"),
}

START = "2002-01"     # inflation expectations begin in the early 2000s
STEPS = 36


# %% Forecast one measure group
# Fit a VAR for each target, project its drivers, and save combined results.
def _run_group(measures, filename, verbose):
    drivers = build_frame(DRIVERS, freq="M", start=START)
    results = {}
    for label, column in measures.items():
        target = series("KR", "M", column, name="cpi").loc[pd.Period(START, freq="M"):]
        frame = pd.concat([target, drivers], axis=1).dropna()
        frame = pct_change(frame, ["cpi", "oil", "import_prices"]).dropna()

        # expectations start in 2002, so the sample is a little shorter than
        # the other monthly models; 12 candidate lags still fit comfortably
        res = fit_var(frame, maxlags=12, ic="aic")
        mid, _lo, _hi = forecast(res, STEPS)
        results[label] = report(target.loc[frame.index[0]:], mid["cpi"], label)

        if verbose:
            last = results[label][results[label]["is_forecast"]].iloc[-1]
            print(f"   {label:10s} VAR({res.k_ar})  "
                  f"sample {frame.index[0]}-{frame.index[-1]}  "
                  f"forecast to {results[label].index[-1]}: "
                  f"{last[f'{label}_yoy']:.2f}% y/y")

    combined = pd.concat([r[[c for c in r.columns if c.endswith(("_index", "_yoy"))]]
                          for r in results.values()], axis=1)
    combined.to_csv(RESULTS / filename)
    return combined


# %% Country forecast entry points
# Expose the CPI and PPI forecast runs separately.
def run_cpi(verbose=True):
    return _run_group(CPI_MEASURES, "kr_cpi_inflation_forecast.csv", verbose)


def run_ppi(verbose=True):
    return _run_group(PPI_MEASURES, "kr_ppi_inflation_forecast.csv", verbose)


# %% Direct script execution
# Run both forecast groups when this file is executed on its own.
if __name__ == "__main__":
    print("== KR CPI ==")
    run_cpi()
    print("== KR PPI ==")
    run_ppi()
