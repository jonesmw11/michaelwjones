# Korea MCT input preparation: national CPI division panel and official core context.

# =============================================================================
# %% Imports and paths
import json
import re
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from scipy.io import savemat

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


# =============================================================================
# %% Read the current KOSIS national division panel
source = pd.read_csv(ROOT / "source/kosis_division_cpi_1985_2026.csv", encoding="utf-8-sig")
period_columns = [column for column in source if re.match(r"M\d{6} ", column)]
periods = pd.to_datetime([column.split(" ", 1)[1] for column in period_columns], format="%Y.%m")
labels = source["I by Expenditure Category"].str.replace(r"^[A-L] ", "", regex=True).str.replace(r"^\d{2} ", "", regex=True)
levels = pd.DataFrame(source.loc[1:, period_columns].to_numpy(dtype=float).T, index=periods, columns=labels.iloc[1:])
assert levels.shape[1] == 12 and not levels.isna().any().any()


# =============================================================================
# %% Build annualized inflation and division-level core weights
inflation = 100 * ((levels / levels.shift(1)) ** 12 - 1)
inflation = inflation.dropna()
published_weights = pd.read_csv(ROOT.parent / "korea_official/division_weights.csv")["Basket share"].to_numpy()
core_mask = np.ones(12, dtype=bool)
core_mask[0] = False
weight_vector = np.where(core_mask, published_weights, 0.0)
weight_vector /= weight_vector.sum()
weights = np.tile(weight_vector, (len(inflation), 1))
headline_yoy = source.loc[0, period_columns].to_numpy(dtype=float)
headline_yoy = pd.Series(headline_yoy, index=periods).pct_change(12, fill_method=None).reindex(inflation.index).to_numpy() * 100


# =============================================================================
# %% Load the official food-and-energy-excluded series for comparison
book = openpyxl.load_workbook(ROOT.parent / "Korea - Core Inflation Measures.xlsx", data_only=True, read_only=True)
sheet = book["Korea M"]
rows = list(sheet.values)
official = pd.Series(
    [row[1] for row in rows[1:] if row[0] and row[1] is not None],
    index=pd.to_datetime([row[0] for row in rows[1:] if row[0] and row[1] is not None]),
    dtype=float,
)
book.close()
official_core_yoy = official.pct_change(12, fill_method=None).reindex(inflation.index).to_numpy() * 100


# =============================================================================
# %% Save self-contained model inputs and audit files
limitation = "Division-level proxy: food is excluded exactly, but energy remains embedded within housing and transport because a current detailed component panel is not stored locally."
savemat(DATA / "korea_core.mat", {
    "y": inflation.to_numpy(),
    "weights": weights,
    "period_codes": np.array(inflation.index.strftime("%Y-%m"), dtype=object),
    "labels": np.array(inflation.columns, dtype=object),
    "core_mask": core_mask,
    "headline_yoy": headline_yoy,
    "official_core_yoy": official_core_yoy,
    "frequency": "M",
    "country": "South Korea",
    "target_name": "Core CPI proxy; official CPI excluding food and energy shown for context",
    "limitation": limitation,
})
inflation.to_csv(DATA / "sector_inflation.csv", date_format="%Y-%m")
pd.DataFrame(weights, index=inflation.index, columns=inflation.columns).to_csv(DATA / "core_weights.csv", date_format="%Y-%m")
pd.DataFrame({"headline_yoy": headline_yoy, "official_core_yoy": official_core_yoy}, index=inflation.index).to_csv(DATA / "context_inflation.csv", date_format="%Y-%m")
pd.DataFrame({
    "name": inflation.columns,
    "included_in_core": core_mask,
    "published_2022_weight": published_weights,
}).to_csv(DATA / "sector_mapping.csv", index=False)

checks = {
    "country": "South Korea",
    "target": "Core CPI proxy with official ex-food-and-energy comparison",
    "first_period": inflation.index[0].strftime("%Y-%m"),
    "last_period": inflation.index[-1].strftime("%Y-%m"),
    "observations": len(inflation),
    "sectors": inflation.shape[1],
    "core_sectors": int(core_mask.sum()),
    "complete_matrix": bool(np.isfinite(inflation.to_numpy()).all()),
    "weights_sum_to_one": bool(np.allclose(weights.sum(axis=1), 1)),
    "limitation": limitation,
}
(ROOT / "input_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
