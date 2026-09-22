# Japan MCT input preparation: national CPI, core excluding fresh food.

# =============================================================================
# %% Imports and paths
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import savemat

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SOURCE = ROOT.parent / "japan_official"


# =============================================================================
# %% Select a disjoint national CPI basket
series = pd.read_csv(SOURCE / "processed/japan_cpi_index.csv")
series["date"] = pd.to_datetime(series["date"])
series = series.set_index("date")

components = {
    "0157": "Fresh food",
    "0172": "Food excluding fresh food",
    "0045": "Housing",
    "0054": "Fuel, light and water charges",
    "0060": "Furniture and household utensils",
    "0082": "Clothes and footwear",
    "0107": "Medical care",
    "0111": "Transportation and communication",
    "0118": "Education",
    "0122": "Culture and recreation",
    "0145": "Miscellaneous",
}
levels = series[list(components)].rename(columns=components)
assert not levels.isna().any().any()


# =============================================================================
# %% Build annualized sector inflation and fixed official weights
inflation = 100 * ((levels / levels.shift(1)) ** 12 - 1)
inflation = inflation.dropna()

raw_weights = {
    "Fresh food": 134252762,
    "Food excluding fresh food": 841550403,
    "Housing": 773321148,
    "Fuel, light and water charges": 247346867,
    "Furniture and household utensils": 131897186,
    "Clothes and footwear": 105807048,
    "Medical care": 165090296,
    "Transportation and communication": 511544532,
    "Education": 110104238,
    "Culture and recreation": 320898162,
    "Miscellaneous": 201944448,
}
core_mask = np.array([name != "Fresh food" for name in inflation.columns])
weight_vector = np.array([raw_weights[name] if keep else 0.0 for name, keep in zip(inflation.columns, core_mask)])
weight_vector /= weight_vector.sum()
weights = np.tile(weight_vector, (len(inflation), 1))

headline_yoy = series["0001"].pct_change(12, fill_method=None).reindex(inflation.index).to_numpy() * 100
official_core_yoy = series["0161"].pct_change(12, fill_method=None).reindex(inflation.index).to_numpy() * 100


# =============================================================================
# %% Save self-contained model inputs and audit files
savemat(DATA / "japan_core.mat", {
    "y": inflation.to_numpy(),
    "weights": weights,
    "period_codes": np.array(inflation.index.strftime("%Y-%m"), dtype=object),
    "labels": np.array(inflation.columns, dtype=object),
    "core_mask": core_mask,
    "headline_yoy": headline_yoy,
    "official_core_yoy": official_core_yoy,
    "frequency": "M",
    "country": "Japan",
    "target_name": "CPI excluding fresh food",
    "limitation": "Uses fixed 2025 official weights across the historical sample.",
})
inflation.to_csv(DATA / "sector_inflation.csv", date_format="%Y-%m")
pd.DataFrame(weights, index=inflation.index, columns=inflation.columns).to_csv(DATA / "core_weights.csv", date_format="%Y-%m")
pd.DataFrame({"headline_yoy": headline_yoy, "official_core_yoy": official_core_yoy}, index=inflation.index).to_csv(DATA / "context_inflation.csv", date_format="%Y-%m")
pd.DataFrame({
    "code": list(components),
    "name": list(components.values()),
    "included_in_core": core_mask,
    "raw_2025_weight": [raw_weights[name] for name in components.values()],
}).to_csv(DATA / "sector_mapping.csv", index=False)

checks = {
    "country": "Japan",
    "target": "CPI excluding fresh food",
    "first_period": inflation.index[0].strftime("%Y-%m"),
    "last_period": inflation.index[-1].strftime("%Y-%m"),
    "observations": len(inflation),
    "sectors": inflation.shape[1],
    "core_sectors": int(core_mask.sum()),
    "complete_matrix": bool(np.isfinite(inflation.to_numpy()).all()),
    "weights_sum_to_one": bool(np.allclose(weights.sum(axis=1), 1)),
}
(ROOT / "input_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
