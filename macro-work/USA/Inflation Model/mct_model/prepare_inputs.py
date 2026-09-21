# Prepare an exact upstream-data replication and a separately labelled current-vintage reconstruction.
#
# MCT PIPELINE MAP
# [1] Source data -> prepare_inputs.py -> data/*.mat
# [2] Python entry -> run_pipeline.py -> run_python.py
# [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
# [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
# [5] Optional validation/reference tooling -> Archive/
# Archived Octave route and downloaded research material are not used in production.
#
# THIS FILE: STAGE 1, INPUT PREPARATION.
# It converts upstream and current official data into validated model-ready matrices.

# %% Imports and project paths
# Load file, numerical, table, and MATLAB-format utilities; establish the local
# input/output folders used by every later pipeline stage.
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.io import loadmat, savemat

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)

# %% Exact October 2023 replication inputs
# Load the NY Fed snapshot, verify its inflation transformations and aggregation
# weights, select the estimation sample, and save an exact replication dataset.
original = loadmat(ROOT / 'upstream/data/pce_m59_202310.mat', simplify_cells=True)
names = original['names'].tolist()
labels = original['labels'].tolist()
dates = pd.date_range('1959-01-01', periods=len(original['p_agg']), freq='MS')
assert dates[-1] == pd.Timestamp('2023-10-01')
sample = dates >= '1960-01-01'
np.testing.assert_allclose(original['infla_disagg'][1:], 100*((original['p_disagg'][1:] / original['p_disagg'][:-1])**12-1), atol=1e-10)
np.testing.assert_allclose(original['share'], original['nom_disagg']/original['nom_disagg'].sum(axis=1)[:, None], atol=1e-14)
core_mask = np.ones(17, dtype=bool)
core_mask[[4, 6, 9]] = False
assert np.all(original['share_xfe'][:, ~core_mask] == 0)
np.testing.assert_allclose(original['share_xfe'].sum(axis=1), 1, atol=1e-12)
saved = {
    'y': original['infla_disagg'][sample], 'weights': original['share_xfe'][sample],
    'headline_yoy': original['infla_12m_agg'][sample], 'core_yoy': original['infla_12m_agg_xfe'][sample],
    'month_codes': dates[sample].year*100+dates[sample].month,
    'labels': np.array(labels, dtype=object), 'core_mask': core_mask,
}
savemat(DATA / 'replication_202310.mat', saved)
pd.DataFrame(saved['y'], index=dates[sample], columns=labels).to_csv(DATA / 'replication_inflation.csv', date_format='%Y-%m')
reference = loadmat(ROOT / 'upstream/results/results_202310.mat', simplify_cells=True)
pd.DataFrame(reference['MCT'], index=dates[sample], columns=['lower','median','upper']).to_csv(DATA / 'reference_202310.csv', date_format='%Y-%m')

# %% Current official BEA source data
# Current BEA data: use the same seventeen-sector order, splitting housing and utilities.
# Load current price-index and spending series that will be mapped into the same
# seventeen-sector ordering as the published replication model.
pce = ROOT.parent / 'pce_official'
meta = pd.read_csv(pce / 'series.csv').set_index('Line')
prices = pd.read_csv(pce / 'monthly_prices.csv', index_col=0, parse_dates=True)
spend = pd.read_csv(pce / 'monthly_spending.csv', index_col=0, parse_dates=True)
prices.columns = prices.columns.astype(int)
spend.columns = spend.columns.astype(int)
levels, dollars, mapping = [], [], []

# %% Reconstruct the seventeen sector histories
# Map each upstream sector to current BEA data. The housing-ex-utilities component
# is reconstructed with a bilateral Fisher chain because the source preparer is unavailable.
for i, code in enumerate(names):
    if i == 8:
        # Housing and water/sanitation excluding electricity/gas: bilateral Fisher aggregation.
        lines = [153, 166]
        assert meta.loc[153, 'Name'] == 'Housing' and meta.loc[166, 'Name'] == 'Water supply and sanitation (25)'
        p, v = prices[lines], spend[lines]
        rel = p.div(p.shift(1))
        laspeyres = (v.shift(1) * rel).sum(axis=1, min_count=2) / v.shift(1).sum(axis=1, min_count=2)
        paasche = v.sum(axis=1, min_count=2) / v.div(rel).sum(axis=1, min_count=2)
        change = np.sqrt(laspeyres * paasche)
        level = change.iloc[1:].cumprod().reindex(p.index)
        level.iloc[0] = 1
        level = level / level.loc['2017'].mean() * 100
        nominal = v.sum(axis=1, min_count=2)
        method = 'Reconstructed bilateral Fisher chain of housing and water/sanitation; NY Fed input-preparation code is not supplied'
    else:
        lines = [169] if i == 9 else [int(meta.index[meta['Price code'].eq(code)][0])]
        level, nominal = prices[lines[0]], spend[lines[0]]
        method = 'Published BEA sector index and current-dollar spending'
    levels.append(level)
    dollars.append(nominal)
    mapping.append(dict(position=i+1, name=labels[i], upstream_code=code, bea_lines=','.join(map(str,lines)),
                        included_in_core=bool(core_mask[i]), method=method))

# %% Calculate current inflation and core weights
# Combine the sector series, annualize monthly price changes, exclude non-core
# sectors from aggregation, normalize weights, and validate the resulting sample.
levels = pd.concat(levels, axis=1); levels.columns = labels
dollars = pd.concat(dollars, axis=1); dollars.columns = labels
assert len(levels.columns) == 17 and not levels.isna().any().any()
y = ((levels/levels.shift(1))**12-1)*100
weights = dollars.copy()
weights.iloc[:, ~core_mask] = 0
weights = weights.div(weights.sum(axis=1), axis=0)
np.testing.assert_allclose(weights.sum(axis=1), 1, atol=1e-12)
sample = y.index >= '1960-01-01'
assert not y.loc[sample].isna().any().any()
core_line = int(meta.index[meta['Price code'].eq('DPCCRG')][0])

# %% Save current model inputs and audit tables
# Write the model-ready MAT file plus human-readable price, inflation, weight,
# and sector-mapping tables used to inspect the reconstructed vintage.
savemat(DATA / 'current_reconstruction.mat', {
    'y': y.loc[sample].values, 'weights': weights.loc[sample].values,
    'headline_yoy': prices[1].pct_change(12, fill_method=None).loc[sample].values*100,
    'core_yoy': prices[core_line].pct_change(12, fill_method=None).loc[sample].values*100,
    'month_codes': y.index[sample].year*100+y.index[sample].month,
    'labels': np.array(labels, dtype=object), 'core_mask': core_mask,
})
levels.to_csv(DATA / 'current_sector_prices.csv', date_format='%Y-%m')
y.loc[sample].to_csv(DATA / 'current_sector_inflation.csv', date_format='%Y-%m')
weights.loc[sample].to_csv(DATA / 'current_core_weights.csv', date_format='%Y-%m')
pd.DataFrame(mapping).to_csv(DATA / 'sector_mapping.csv', index=False)

# %% Record input validation and provenance
# Summarize dates, dimensions, validation results, reconstruction limitations,
# and the source workbook hash for reproducibility.
report = {'replication_first': '1960-01', 'replication_last': '2023-10', 'replication_months': len(saved['y']),
          'current_first': str(y.index[sample][0].date()), 'current_last': str(y.index[-1].date()), 'current_months': int(sample.sum()),
          'sectors': 17, 'core_sectors': int(core_mask.sum()), 'upstream_transform_checks': 'PASS',
          'current_weights_sum_check': 'PASS', 'current_status': 'Reconstruction, not exact replication: housing aggregation preparer unavailable',
          'source_sha256': hashlib.sha256((pce/'raw/Section2All.xlsx').read_bytes()).hexdigest()}
(ROOT / 'input_checks.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
