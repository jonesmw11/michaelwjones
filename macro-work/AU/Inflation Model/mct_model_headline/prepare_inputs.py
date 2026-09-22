# Australia headline MCT input preparation with a longer quarterly history.

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
# %% Form six long-history groups and an exact headline residual
long_group_codes = [1, 34, 41, 53, 65, 91]
required = [0] + long_group_codes
panel = panel[required].dropna()
weights_by_code = hierarchy["weight"]
selected_weight = weights_by_code.loc[long_group_codes].sum()
residual_weight = 1.0 - selected_weight

levels = panel[long_group_codes].copy()
levels.columns = [hierarchy.loc[code, "name"] for code in long_group_codes]
residual_log = (
    np.log(panel[0])
    - np.log(panel[long_group_codes]).mul(weights_by_code.loc[long_group_codes], axis=1).sum(axis=1)
) / residual_weight
levels["Other goods and services"] = np.exp(residual_log)

reconstructed = np.exp(
    np.log(levels.iloc[:, :-1]).mul(weights_by_code.loc[long_group_codes].to_numpy(), axis=1).sum(axis=1)
    + residual_weight * np.log(levels["Other goods and services"])
)
np.testing.assert_allclose(reconstructed, panel[0], rtol=1e-12, atol=1e-12)


# =============================================================================
# %% Build annualized quarterly inflation and headline weights
inflation = 100 * ((levels / levels.shift(1)) ** 4 - 1)
inflation = inflation.dropna()
weight_vector = np.r_[weights_by_code.loc[long_group_codes].to_numpy(), residual_weight]
weight_vector /= weight_vector.sum()
weights = np.tile(weight_vector, (len(inflation), 1))
core_mask = np.ones(inflation.shape[1], dtype=bool)
headline_yoy = panel[0].pct_change(4, fill_method=None).reindex(inflation.index).to_numpy() * 100


# =============================================================================
# %% Save self-contained model inputs and audit files
limitation = "Uses fixed 2025 weights historically. The residual sector is constructed to reproduce the official headline index exactly under the fixed-weight geometric aggregation."
savemat(DATA / "australia_headline.mat", {
    "y": inflation.to_numpy(),
    "weights": weights,
    "period_codes": np.array(inflation.index.astype(str), dtype=object),
    "labels": np.array(inflation.columns, dtype=object),
    "core_mask": core_mask,
    "headline_yoy": headline_yoy,
    "official_core_yoy": np.full(len(inflation), np.nan),
    "frequency": "Q",
    "country": "Australia",
    "target_name": "Headline CPI",
    "limitation": limitation,
})
date_index = inflation.index.to_timestamp(how="end").normalize()
inflation.set_axis(date_index).to_csv(DATA / "sector_inflation.csv", date_format="%Y-%m-%d")
pd.DataFrame(weights, index=date_index, columns=inflation.columns).to_csv(DATA / "headline_weights.csv", date_format="%Y-%m-%d")
pd.DataFrame({"headline_yoy": headline_yoy}, index=date_index).to_csv(DATA / "context_inflation.csv", date_format="%Y-%m-%d")
pd.DataFrame({
    "name": inflation.columns,
    "included_in_core": core_mask,
    "fixed_2025_weight": weight_vector,
}).to_csv(DATA / "sector_mapping.csv", index=False)

checks = {
    "country": "Australia",
    "target": "Headline CPI",
    "frequency": "Quarterly",
    "first_period": str(inflation.index[0]),
    "last_period": str(inflation.index[-1]),
    "observations": len(inflation),
    "sectors": inflation.shape[1],
    "headline_reconstruction": "PASS",
    "complete_matrix": bool(np.isfinite(inflation.to_numpy()).all()),
    "weights_sum_to_one": bool(np.allclose(weights.sum(axis=1), 1)),
    "limitation": limitation,
}
(ROOT / "input_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
