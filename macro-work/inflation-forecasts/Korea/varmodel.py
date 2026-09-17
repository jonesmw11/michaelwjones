"""VAR modelling helpers built directly on statsmodels' VAR.

Everything here is a thin, documented wrapper around
`statsmodels.tsa.api.VAR`, which does the real work:
  - `VAR(data).fit(maxlags=..., ic=...)` estimates the model (OLS per
    equation, exactly as VAR theory prescribes) and can pick the lag order
    itself by AIC/BIC/HQIC,
  - `results.forecast(y, steps)` produces the dynamic multi-step forecast,
    feeding each period's prediction back in as the next period's lag,
  - `results.forecast_interval(...)` gives asymptotic confidence bands.

The only thing added on top is bookkeeping: turning inflation-rate forecasts
back into index levels and year-on-year rates, which is how the results are
reported.
"""
# %% Imports and data transforms
# Load numerical, tabular, and statsmodels VAR tools.
import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR

from data import yoy


# %% VAR estimation
# Fit each stationary input frame and retain its labels and sample dates.
def fit_var(data, maxlags=6, ic="aic", lags=None):
    """Estimate a VAR on a stationary frame (inflation rates, unemployment...).

    data    : DataFrame of the model's variables, no missing values
    maxlags : largest lag order considered when selecting automatically
    ic      : information criterion for automatic lag choice
              ("aic", "bic", "hqic", "fpe"); ignored when `lags` is given
    lags    : fix the lag order explicitly instead of selecting it

    Returns the fitted statsmodels VARResults object.
    """
    clean = data.dropna()
    # pass the plain array: the period index is kept separately below, and
    # statsmodels only needs dates for labelling
    model = VAR(clean.to_numpy())
    if lags is not None:
        res = model.fit(lags)
    else:
        res = model.fit(maxlags=maxlags, ic=ic)
    # keep the column names with the result for readable output
    res.model.data.param_names = list(clean.columns)
    res._columns = list(clean.columns)
    res._index = clean.index
    return res


# %% Dynamic VAR projection
# Forecast all endogenous variables over the requested horizon.
def forecast(res, steps, alpha=0.05):
    """Dynamic multi-step forecast from a fitted VAR.

    Uses statsmodels' own recursion (`forecast_interval`), so the drivers are
    projected jointly with inflation - no external assumption paths.
    Returns (point forecast, lower band, upper band) as DataFrames indexed by
    the periods that follow the estimation sample.
    """
    cols, idx = res._columns, res._index
    y = res.model.endog[-res.k_ar:]                     # last k_ar observations
    mid, lower, upper = res.forecast_interval(y, steps, alpha=alpha)
    # the estimation index ends at the last complete observation, so the
    # forecast periods follow directly from it
    future = pd.period_range(idx[-1] + 1, periods=steps, freq=idx.freqstr)
    mk = lambda a: pd.DataFrame(a, index=future, columns=cols)
    return mk(mid), mk(lower), mk(upper)


# %% Forecast index reconstruction
# Chain projected period changes onto the last observed price index.
def rates_to_index(last_level, rate_path):
    """Chain a forecast of period-on-period % changes onto the last observed
    index level, producing a continuous index into the future."""
    out = {}
    level = last_level
    for period, rate in rate_path.items():
        level = level * (1.0 + rate / 100.0)
        out[period] = level
    return pd.Series(out)


# %% Historical and forecast reporting
# Combine index levels and year-ended rates with an actual/forecast flag.
def report(history_level, rate_forecast, label):
    """Combine history and forecast into one index, then report YoY inflation.

    history_level : the observed price index (Series)
    rate_forecast : forecast of its % change per period (Series)
    Returns a DataFrame with the index level and YoY rate, flagged so you can
    see which rows are actual and which are forecast.
    """
    # workbook sheets are padded with blank rows beyond the last release, so
    # trim to the last genuine observation before chaining the forecast on
    history_level = history_level.dropna()
    fut = rates_to_index(history_level.iloc[-1], rate_forecast)
    full = pd.concat([history_level, fut])
    out = pd.DataFrame({f"{label}_index": full, f"{label}_yoy": yoy(full)})
    out["is_forecast"] = [False] * len(history_level) + [True] * len(fut)
    return out


# %% Lag-order diagnostics
# Summarize information criteria for candidate VAR lag orders.
def lag_order_table(data, maxlags=8):
    """Lag-order selection summary (AIC/BIC/FPE/HQIC) for the write-up."""
    clean = data.dropna()
    return VAR(clean.to_numpy()).select_order(maxlags).summary()
