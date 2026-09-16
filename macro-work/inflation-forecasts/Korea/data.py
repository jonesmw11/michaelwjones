# Read the country-specific Data Inputs.xlsx beside this module.
# Row 1 contains series names, row 2 is skipped, and data begins on row 3.
# Date is in column B for AU, AU-M, and KR; column A for JN.

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WORKBOOK = HERE / "Data Inputs.xlsx"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

# sheets whose first column is already the date (no year label column)
_DATE_IN_COL_A = {"JN", "JN-M", "NZ-M"}


def load_sheet(sheet, freq):
    """Read one country sheet into a DataFrame indexed by period.

    Parameters
    ----------
    sheet : str   sheet name in Data Inputs.xlsx (e.g. "AU-M", "KR")
    freq  : str   "M" for monthly data, "Q" for quarterly

    Returns a DataFrame whose columns are the workbook's series names
    (duplicates suffixed by pandas) and whose index is a PeriodIndex.
    """
    raw = pd.read_excel(WORKBOOK, sheet_name=sheet, header=None)
    names = raw.iloc[0]                       # row 1 holds the series names
    body = raw.iloc[2:].copy()                # data starts on row 3
    date_col = 0 if sheet in _DATE_IN_COL_A else 1
    dates = pd.to_datetime(body.iloc[:, date_col], errors="coerce")

    df = body.iloc[:, date_col + 1:].copy()
    # some sheets repeat a heading (e.g. "SG CPI" three times); keep the first
    # occurrence and suffix later ones so every column is addressable
    seen, cols = {}, []
    for n in names.iloc[date_col + 1:]:
        base = str(n).strip()
        if base in seen:
            seen[base] += 1
            cols.append(f"{base} ({seen[base]})")
        else:
            seen[base] = 0
            cols.append(base)
    df.columns = cols
    df = df.apply(pd.to_numeric, errors="coerce")     # text/#VALUE! -> NaN
    df.index = pd.PeriodIndex(dates, freq=freq)
    df = df[df.index.notna()]
    df = df.loc[:, [c for c in df.columns if c and not c.startswith("nan")]]
    return df.groupby(level=0).first()                # collapse any dupe rows


def series(sheet, freq, column, name=None, zero_is_missing=True):
    """Pull one named series out of a sheet, dropping empty observations.

    `zero_is_missing` guards against a workbook quirk: a few price-index
    columns carry a stray 0 where a value was never filled in (Japan's
    national CPI has one). A price index is never legitimately zero, and a
    single zero would otherwise produce a -100% inflation reading that
    poisons the whole model, so zeros are treated as missing.
    """
    df = load_sheet(sheet, freq)
    if column not in df.columns:
        raise KeyError(f"'{column}' not in sheet {sheet}. Available: "
                       f"{[c for c in df.columns][:40]}")
    s = df[column]
    if zero_is_missing:
        s = s.replace(0.0, np.nan)
    s = s.dropna()
    s.name = name or column
    return s


def to_quarterly(s, how="mean"):
    """Convert a monthly series to quarterly (mean of the months by default;
    'last' takes the final month, appropriate for index levels)."""
    g = s.groupby(s.index.asfreq("Q"))
    out = g.mean() if how == "mean" else g.last()
    out.name = s.name
    return out


def build_frame(specs, freq, start=None):
    """Assemble a modelling frame from several (sheet, column) specs.

    specs: {model variable name: (sheet, column)} - all read at `freq`.
    Returns a DataFrame trimmed to the rows where every variable exists,
    which is what the VAR needs.
    """
    # expectations and dummies can legitimately be zero; price indices cannot
    zero_ok = {"expectations", "subsidy", "dummy"}
    cols = {}
    for var, (sheet, column) in specs.items():
        cols[var] = series(sheet, freq, column, name=var,
                           zero_is_missing=not any(k in var for k in zero_ok))
    # align on the union of dates (each series was trimmed of its own blanks,
    # so they can start and end at different points)
    df = pd.concat(cols.values(), axis=1, join="outer").sort_index()
    df.columns = list(cols)
    if start is not None:
        df = df.loc[pd.Period(start, freq=freq):]
    return df


def pct_change(df, cols):
    """Percent change (x100) of the named columns - the standard transform
    that turns a price INDEX into an inflation RATE for the VAR."""
    out = df.copy()
    for c in cols:
        out[c] = 100.0 * out[c].pct_change()
    return out


def yoy(level):
    """Year-on-year percent change of an index level."""
    n = 12 if level.index.freqstr.startswith("M") else 4
    return 100.0 * (level / level.shift(n) - 1.0)
