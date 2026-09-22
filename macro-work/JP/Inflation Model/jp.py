# Japan inflation forecasts: national and Tokyo CPI monthly VARs.
# Data Inputs.xlsx, JN: CPI, unemployment, Tankan expectations, oil,
# import prices and Stage 2. Expectations and unemployment are percentage
# levels; oil is USD per barrel; CPI, import prices and Stage 2 use m/m changes.
# Tankan is held forward from the month after each quarter, starting April
# 2014. See TANKAN.md for source and timing. Lags are selected by AIC.
# =============================================================================
# %% Imports and data access
# Load pandas and the local workbook and VAR helpers.
import pandas as pd

from data import build_frame, pct_change, series, RESULTS
from varmodel import fit_var, forecast, report

# %% Model configuration
# Define national and Tokyo CPI measures, shared drivers, sample, and horizon.
NATIONAL = {
    "headline": "Japan CPI Headline",
    "ex_fresh_food": "Japan CPI ex Fresh Food",
    "ex_fresh_food_energy": "Japan CPI ex Fresh Food and Energy",
    "ex_food_energy": "Japan CPI ex Food and Energy",
}

TOKYO = {
    "tokyo_headline": "Tokyo CPI Headline",
    "tokyo_ex_fresh_food": "Tokyo CPI ex Fresh Food",
    "tokyo_ex_fresh_food_energy": "Tokyo CPI ex Fresh Food and Energy",
}

DRIVERS = {
    "unemployment": ("JN", "Unemployment"),
    "expectations": ("JN", "Tankan inflation expectations"),
    "oil": ("JN", "WTI spot USD"),
    "import_prices": ("JN", "JP ImPI"),
    "stage2": ("JN", "Stage2"),
}

START = "2000-01"
STEPS = 36


# %% Forecast one measure group
# Fit a VAR for each target, project its drivers, and save combined results.
def _run_group(measures, filename, verbose):
    drivers = build_frame(DRIVERS, freq="M", start=START)
    results = {}
    for label, column in measures.items():
        cpi = series("JN", "M", column, name="cpi").loc[pd.Period(START, freq="M"):]
        frame = pd.concat([cpi, drivers], axis=1).dropna()
        # CPI and other price indices -> inflation rates; oil, unemployment and expectations stay in levels
        frame = pct_change(frame, ["cpi", "import_prices", "stage2"]).dropna()

        res = fit_var(frame, maxlags=12, ic="aic")
        mid, _lo, _hi = forecast(res, STEPS)
        # Chain from the common VAR cutoff; Tokyo can have a newer CPI release.
        results[label] = report(cpi.loc[frame.index[0]:frame.index[-1]], mid["cpi"], label)

        if verbose:
            out = results[label]
            last = out[out["is_forecast"]].iloc[-1]
            print(f"   {label:28s} VAR({res.k_ar})  "
                  f"sample {frame.index[0]}-{frame.index[-1]}  "
                  f"forecast to {out.index[-1]}: {last[f'{label}_yoy']:.2f}% y/y")

    combined = pd.concat([r[[c for c in r.columns if c.endswith(("_index", "_yoy"))]]
                          for r in results.values()], axis=1)
    combined.to_csv(RESULTS / filename)
    return combined


# %% Country forecast entry points
# Expose the national and Tokyo forecast runs separately.
def run_national(verbose=True):
    return _run_group(NATIONAL, "jp_cpi_inflation_forecast.csv", verbose)


def run_tokyo(verbose=True):
    return _run_group(TOKYO, "jp_tokyo_inflation_forecast.csv", verbose)


# %% Direct script execution
# Run both forecast groups when this file is executed on its own.
if __name__ == "__main__":
    print("== JP national CPI ==")
    run_national()
    print("== JP Tokyo CPI ==")
    run_tokyo()
