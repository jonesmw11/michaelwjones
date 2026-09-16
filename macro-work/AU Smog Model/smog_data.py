"""Build SMOG model inputs for every country from Model Inputs.xlsx.

This replaces the EViews "Run Completed Model" data step. Each country's
transforms are taken from its original .prg, so the variables handed to the
Kalman filter are the same ones EViews would have produced - but built in
Python, with no workfile dependency.

The model coefficients are already stored in the country files (au.py, jn.py,
...). Combined with the data built here, that is everything needed to run the
models forward to the latest available quarter.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
MODEL_INPUTS = HERE / "Model Inputs.xlsx"

# --------------------------------------------------------------------------
# Sheet layouts: the columns each country's .prg imports, in workbook order.
# The sheets have no usable header row, so columns are named positionally
# starting at column C (the date sits in column B).
# --------------------------------------------------------------------------

SHEETS = {
    "AU": ("AU - Q", [
        "real_gdp_sa", "real_gdp_non_farm_sa", "import_price_deflator", "cpi_all_nsa",
        "cpi_all_sa", "cpi_trimmed_spliced", "core_cpi_index", "cpi_core_inflation",
        "cpi_core_inflation_avg", "unemployment", "covid_d", "labour",
        "expectations_melb", "expectations_union", "expectations_comb",
        "policy_rate", "ssr", "cpi_core_inflation_forecast", "real_gni"]),
    "JN": ("JN - Q", [
        "real_gdp_sa", "nom_gdp_sa", "labour", "labour_sa", "cpi_core_sa",
        "cpi_core_core_sa", "cpi_core_core_forecast", "unemployment",
        "expectations_tankan", "covid_d", "import_price_deflator", "interest", "ssr"]),
    "KR": ("KR - Q", [
        "real_gdp_sa", "labour_nsa", "labour_sa", "cpi_sa", "cpi_core_sa",
        "unemployment", "expectations_bok", "covid_d", "import_price_deflator",
        "policy_rate", "index_forecast"]),
    "NZ": ("NZ - Q", [
        "real_gdp_sa", "import_price_deflator", "lab_cost_index", "cpi_all_sa",
        "unemployment", "expectations_one", "expectations_two", "covid_d"]),
    "SG": ("SG - Q", [
        "real_gdp_sa", "labour_nsa", "labour_sa", "cpi_core_sa", "unemployment",
        "covid_d", "import_price_deflator_nsa", "import_price_deflator_sa",
        "cpi_core_forecast"]),
    "TW": ("TW - Q", [
        "gdp_sa", "unemployment", "import_price_deflator", "cpi_headline",
        "cpi_core_sa", "policy_rate", "cpi_core_fcast", "ulc", "covid_d",
        "core_infl", "expectations"]),
    "US": ("US - Q", [
        "real_gdp_sa", "labour", "cdm_import_price_deflator",
        "fred_import_price_deflator", "pce_core", "pce_core_inflation",
        "expectations_pce_core_avg", "expectations_mich", "unemployment",
        "oil_prices", "import_prices", "policy_rate", "covid_d",
        "pce_core_forecast", "laubach", "domestic_demand",
        "domestic_demand_less_inventories"]),
}

#: Quarter the inflation-targeting dummy switches on (None = no dummy).
TARGETING_START = {"AU": "1993Q1", "JN": "2012Q4", "US": "2007Q4",
                   "KR": None, "NZ": None, "SG": None, "TW": None}


def pcy(x):
    """Year-ended percent change (EViews @pcy)."""
    return 100.0 * (x / x.shift(4) - 1.0)


def load_sheet(cc):
    """Read one country's quarterly sheet into a period-indexed frame."""
    sheet, cols = SHEETS[cc]
    df = pd.read_excel(MODEL_INPUTS, sheet_name=sheet, skiprows=2, header=None,
                       usecols=range(1, len(cols) + 2),
                       names=["date"] + cols)
    df = df[df["date"].notna()]
    df["date"] = pd.PeriodIndex(pd.to_datetime(df["date"]), freq="Q")
    df = df.set_index("date")
    df = df[~df.index.duplicated(keep="first")]
    return df.apply(pd.to_numeric, errors="coerce")


def hp_trend(series, lamb=1000.0, end=None, boost=1):
    """Boosted Hodrick-Prescott trend, as used for the model's priors."""
    x = series.loc[:end].dropna() if end else series.dropna()
    cycle, trend = sm.tsa.filters.hpfilter(x, lamb=lamb)
    for _ in range(boost):
        cycle, _ = sm.tsa.filters.hpfilter(cycle, lamb=lamb)
        trend = x - cycle
    return trend.reindex(series.index)


def build(cc, end=None):
    """Build the modelling variables for one country.

    Transforms follow that country's original EViews programme exactly.
    `end` trims the sample to the last quarter of actual data.

    Returns a frame with the observables (y, u, pi, pi_e), the exogenous
    drivers, and HP-based priors for the unobserved states (ham_*).
    """
    raw = load_sheet(cc)
    d = pd.DataFrame(index=raw.index)

    # ---- output, inflation and expectations (country-specific) -----------
    if cc == "AU":
        d["y"] = np.log(raw["real_gdp_non_farm_sa"])
        cpi = raw["cpi_trimmed_spliced"]
        d["pi"] = pcy(cpi)
        d["pi_e"] = d["pi"].rolling(4).mean()
        d["delta_nulc"] = pcy(raw["labour"])
        d["delta_4_pm"] = raw["import_price_deflator"] - raw["import_price_deflator"].shift(4)

    elif cc == "JN":
        d["y"] = np.log(raw["real_gdp_sa"])
        d["pi"] = pcy(raw["cpi_core_sa"])
        d["pi_e"] = raw["expectations_tankan"]
        d["delta_nulc"] = pcy(raw["labour_sa"])
        d["delta_4_pm"] = raw["import_price_deflator"] - raw["import_price_deflator"].shift(4)

    elif cc == "KR":
        d["y"] = np.log(raw["real_gdp_sa"])
        d["pi"] = pcy(raw["cpi_core_sa"])
        d["pi_e"] = raw["expectations_bok"]
        d["delta_nulc"] = pcy(raw["labour_sa"])
        d["delta_4_pm"] = raw["import_price_deflator"] - raw["import_price_deflator"].shift(4)

    elif cc == "NZ":
        d["y"] = np.log(raw["real_gdp_sa"])
        d["pi"] = pcy(raw["cpi_all_sa"])
        # NZ averages its two expectations surveys
        d["pi_e"] = (raw["expectations_one"] + raw["expectations_two"]) / 2
        d["delta_nulc"] = pcy(raw["lab_cost_index"])
        d["delta_4_pm"] = raw["import_price_deflator"] - raw["import_price_deflator"].shift(4)

    elif cc == "SG":
        d["y"] = np.log(raw["real_gdp_sa"])
        cpi = raw["cpi_core_sa"]
        d["pi"] = pcy(cpi)
        d["pi_e"] = d["pi"].rolling(4).mean()
        d["delta_nulc"] = pcy(raw["labour_sa"])
        d["delta_4_pm"] = (raw["import_price_deflator_sa"]
                           - raw["import_price_deflator_sa"].shift(4))

    elif cc == "TW":
        d["y"] = np.log(raw["gdp_sa"])
        d["pi"] = pcy(raw["cpi_headline"])
        d["pi_e"] = raw["expectations"]
        d["delta_nulc"] = pcy(raw["ulc"])
        # NOTE: the TW programme uses d(import_price_deflator, 4) - a fourth
        # difference, not the 4-quarter change the other countries use.
        d["delta_4_pm"] = raw["import_price_deflator"].diff().diff().diff().diff()

    elif cc == "US":
        # US works in domestic demand less inventories, logged and x100
        d["y"] = np.log(raw["domestic_demand_less_inventories"]) * 100.0
        d["pi"] = pcy(raw["pce_core"])
        d["pi_e"] = raw["expectations_mich"]
        d["delta_nulc"] = pcy(raw["labour"])
        pm = raw["fred_import_price_deflator"]
        d["delta_4_pm"] = pm - pm.shift(4)

    d["u"] = raw["unemployment"]
    d["covid_d"] = raw["covid_d"].fillna(0.0)

    # ---- priors for the unobserved states --------------------------------
    if cc == "US":
        # The US model takes its trend from the published Laubach gap rather
        # than an HP filter of output, and uses a much smoother NAIRU filter.
        d["ham_u_star"] = hp_trend(d["u"], lamb=50000.0, end=end, boost=11)
        d["ham_y_star"] = d["y"] + raw["laubach"]
        d["ham_gap"] = raw["laubach"]
    else:
        d["ham_u_star"] = hp_trend(d["u"], end=end)
        d["ham_y_star"] = hp_trend(d["y"], end=end)
        d["ham_gap"] = d["y"] - d["ham_y_star"]

    # ---- inflation-targeting dummy ---------------------------------------
    start = TARGETING_START[cc]
    d["d_it"] = ((d.index > pd.Period(start, freq="Q")).astype(float)
                 if start else 0.0)

    return d.loc[:end] if end else d


#: Last quarter of ACTUAL data per country (GDP is normally the binding series).
LAST_ACTUAL = {"AU": "2026Q1", "JN": "2026Q1", "KR": "2026Q1", "NZ": "2025Q4",
               "SG": "2026Q1", "TW": "2025Q4", "US": "2026Q1"}


if __name__ == "__main__":
    for cc in SHEETS:
        d = build(cc, end=LAST_ACTUAL[cc])
        core = d[["y", "u", "pi", "pi_e"]].dropna()
        print(f"{cc}: {len(d)} quarters to {d.index[-1]}, "
              f"complete observables {core.index[0]}-{core.index[-1]}")
