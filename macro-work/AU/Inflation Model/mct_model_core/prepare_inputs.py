# Australia MCT input preparation: quarterly national CPI, core excluding food and energy.

# =============================================================================
# %% Imports and paths
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from scipy.io import savemat

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SOURCE = ROOT.parent / "australia_official"


# =============================================================================
# %% Read the official quarterly national CPI panel
hierarchy = pd.read_csv(SOURCE / "hierarchy_weights.csv").set_index("code")
workbook = openpyxl.load_workbook(SOURCE / "raw/6401018.xlsx", data_only=True, read_only=True)
records = []
for sheet in workbook:
    if not sheet.title.startswith("Data"):
        continue
    rows = list(sheet.values)
    for column in range(1, len(rows[0])):
        if rows[4][column] != "Quarter" or rows[1][column] != "Index Numbers":
            continue
        values = {
            str(pd.Period(row[0], freq="Q")): float(row[column])
            for row in rows[10:]
            if isinstance(row[0], datetime) and isinstance(row[column], (float, int))
        }
        records.append(values)
workbook.close()
assert len(records) == len(hierarchy) == 132
panel = pd.DataFrame(records).T.sort_index()
panel.index = pd.PeriodIndex(panel.index, freq="Q")
panel.columns = hierarchy.index


# =============================================================================
# %% Split energy from housing and transport
group_codes = hierarchy.loc[hierarchy.depth.eq(1)].index.tolist()
energy_codes = [63, 64, 95]
required = [0] + group_codes + energy_codes
panel = panel[required].dropna()
weights_by_code = hierarchy["weight"]

def residual_index(group_code, excluded_codes):
    group_weight = weights_by_code.loc[group_code]
    excluded_weight = weights_by_code.loc[excluded_codes].sum()
    numerator = group_weight * np.log(panel[group_code])
    numerator -= np.log(panel[excluded_codes]).mul(weights_by_code.loc[excluded_codes], axis=1).sum(axis=1)
    return np.exp(numerator / (group_weight - excluded_weight))

energy = np.exp(
    np.log(panel[energy_codes]).mul(weights_by_code.loc[energy_codes], axis=1).sum(axis=1)
    / weights_by_code.loc[energy_codes].sum()
)

levels = pd.DataFrame(index=panel.index)
for code in group_codes:
    name = hierarchy.loc[code, "name"]
    if code == 53:
        levels["Housing excluding household energy"] = residual_index(53, [63, 64])
    elif code == 91:
        levels["Transport excluding automotive fuel"] = residual_index(91, [95])
    else:
        levels[name] = panel[code]
levels["Energy"] = energy


# =============================================================================
# %% Build annualized quarterly inflation and core weights
inflation = 100 * ((levels / levels.shift(1)) ** 4 - 1)
inflation = inflation.dropna()
sector_weights = {}
for code in group_codes:
    name = hierarchy.loc[code, "name"]
    if code == 53:
        sector_weights["Housing excluding household energy"] = weights_by_code.loc[53] - weights_by_code.loc[[63, 64]].sum()
    elif code == 91:
        sector_weights["Transport excluding automotive fuel"] = weights_by_code.loc[91] - weights_by_code.loc[95]
    else:
        sector_weights[name] = weights_by_code.loc[code]
sector_weights["Energy"] = weights_by_code.loc[energy_codes].sum()

excluded = {"Food and non-alcoholic beverages", "Energy"}
core_mask = np.array([name not in excluded for name in inflation.columns])
weight_vector = np.array([sector_weights[name] if keep else 0.0 for name, keep in zip(inflation.columns, core_mask)])
weight_vector /= weight_vector.sum()
weights = np.tile(weight_vector, (len(inflation), 1))
headline_yoy = panel[0].pct_change(4, fill_method=None).reindex(inflation.index).to_numpy() * 100


# =============================================================================
# %% Save self-contained model inputs and audit files
savemat(DATA / "australia_core.mat", {
    "y": inflation.to_numpy(),
    "weights": weights,
    "period_codes": np.array(inflation.index.astype(str), dtype=object),
    "labels": np.array(inflation.columns, dtype=object),
    "core_mask": core_mask,
    "headline_yoy": headline_yoy,
    "official_core_yoy": np.full(len(inflation), np.nan),
    "frequency": "Q",
    "country": "Australia",
    "target_name": "CPI excluding food and energy",
    "limitation": "Quarterly implementation with fixed 2025 weights; historical housing and transport are geometrically decomposed using current component weights.",
})
date_index = inflation.index.to_timestamp(how="end").normalize()
inflation.set_axis(date_index).to_csv(DATA / "sector_inflation.csv", date_format="%Y-%m-%d")
pd.DataFrame(weights, index=date_index, columns=inflation.columns).to_csv(DATA / "core_weights.csv", date_format="%Y-%m-%d")
pd.DataFrame({"headline_yoy": headline_yoy}, index=date_index).to_csv(DATA / "context_inflation.csv", date_format="%Y-%m-%d")
pd.DataFrame({
    "name": inflation.columns,
    "included_in_core": core_mask,
    "fixed_2025_weight": [sector_weights[name] for name in inflation.columns],
}).to_csv(DATA / "sector_mapping.csv", index=False)

checks = {
    "country": "Australia",
    "target": "CPI excluding food and energy",
    "frequency": "Quarterly",
    "first_period": str(inflation.index[0]),
    "last_period": str(inflation.index[-1]),
    "observations": len(inflation),
    "sectors": inflation.shape[1],
    "core_sectors": int(core_mask.sum()),
    "complete_matrix": bool(np.isfinite(inflation.to_numpy()).all()),
    "weights_sum_to_one": bool(np.allclose(weights.sum(axis=1), 1)),
}
(ROOT / "input_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
