# Merge official KOSIS CSV exports without an API key.
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description='Import KOSIS DT_1J22001 exports and rebuild the history workbook.')
parser.add_argument('exports', nargs='*', type=Path)
args = parser.parse_args()
for path in args.exports:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:12]
    target = ROOT / 'raw' / f'history_import_{digest}.csv'
    if not target.exists():
        shutil.copyfile(path, target)

code_col = '[I]by Expenditure Category'
name_col = 'by Expenditure Category'
panels, metadata, sources = [], [], []
for path in sorted((ROOT / 'raw').glob('history_*.csv'), key=lambda p: p.stat().st_mtime):
    frame = pd.read_csv(path, encoding='utf-8-sig', dtype=str)
    required = {code_col, name_col, '[C]by City', 'UNIT'}
    if not required.issubset(frame.columns):
        raise ValueError(f'{path.name}: expected English export with Including code selected')
    if set(frame['[C]by City']) != {'T10'} or set(frame['UNIT']) != {'2020=100'}:
        raise ValueError(f'{path.name}: expected national CPI, 2020=100')
    if frame[code_col].duplicated().any():
        raise ValueError(f'{path.name}: duplicate series codes')
    months = [c for c in frame if re.fullmatch(r'\d{4}\.\d{2} Month', c)]
    if not months:
        raise ValueError(f'{path.name}: no monthly observations')
    panel = frame.set_index(code_col)[months].T
    panel.index = pd.to_datetime([c[:7] for c in months], format='%Y.%m')
    panel = panel.replace({'-': None, '...': None, 'X': None, '': None})
    panel = panel.apply(pd.to_numeric, errors='raise')
    panels.append(panel)
    metadata.append(frame[[code_col, name_col]].rename(columns={code_col: 'Code', name_col: 'Name'}))
    sources.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'first_month': str(panel.index.min().date()), 'last_month': str(panel.index.max().date()),
                    'series': len(panel.columns)})

if not panels:
    raise ValueError('No history exports found')
history = panels[0]
for panel in panels[1:]:
    # Newer nonmissing observations supersede older exports; missing values never erase data.
    history = panel.combine_first(history)
history = history.sort_index().reindex(pd.date_range(history.index.min(), history.index.max(), freq='MS'))
history.index.name = 'Month'
meta = pd.concat(metadata).drop_duplicates('Code', keep='last').set_index('Code').sort_index()
history = history.reindex(columns=meta.index)
meta['Tier'] = [0 if c == '0' else {1: 1, 3: 2, 4: 3, 6: 4}.get(len(c), -1) for c in meta.index]
if (meta['Tier'] < 0).any():
    raise ValueError('Unrecognised classification code lengths')
meta['First observation'] = [history[c].first_valid_index() for c in meta.index]
meta['Last observation'] = [history[c].last_valid_index() for c in meta.index]
meta['Observations'] = history.notna().sum()
complete = len(meta) == 581 and history.index.min() == pd.Timestamp('1965-01-01') and history.index.max() >= pd.Timestamp('2026-08-01') and history['0'].notna().all()
status = 'FULL TABLE PERIOD IMPORTED' if complete else 'PARTIAL HISTORY — additional exports required'
output = ROOT.parent / ('Korea CPI - History.xlsx' if complete else 'Korea CPI - Partial History.xlsx')
notes = [status,
         f'Imported period: {history.index.min():%Y-%m} to {history.index.max():%Y-%m}; {len(meta)} available series.',
         'Monthly national CPI levels, 2020=100. Empty cells mean no published observation; no imputation.',
         'Each tier sheet contains only that classification level. Columns use official KOSIS codes; names are in Series.',
         'YoY and MoM sheets are percentage changes computed from the index, with no forward filling.',
         'Weights sheets contain the official 2022 basket weights, divided by 1000; these are not historical weight vintages.',
         'Intermediate tier weights have NOT yet been joined: a verified Korean-label-to-code crosswalk is required.',
         'All-period availability is not expected for every item. Consult Series for individual coverage.',
         'Source: https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1J22001&language=en',
         'Weights: https://www.mods.go.kr/twcp/file/cpi_dl_2022.xlsx']
weights = pd.read_excel(ROOT / 'raw/weights_2022.xlsx', sheet_name=0, header=None).iloc[3:, 1:4].copy()
weights.columns = ['Division', 'Item', 'Published weight per 1000']
weights['Published weight per 1000'] = pd.to_numeric(weights['Published weight per 1000'])
weights['Basket share'] = weights['Published weight per 1000'] / 1000
divisions = weights.groupby('Division', sort=False)[['Published weight per 1000', 'Basket share']].sum()
assert len(weights) == 458 and len(divisions) == 12
assert abs(weights['Basket share'].sum() - 1) < 1e-12
assert abs(divisions['Basket share'].sum() - 1) < 1e-12
checks = {'history_status': status, 'months': len(history), 'series': len(meta), 'observations': int(history.notna().sum().sum()),
          'tier_counts': meta['Tier'].value_counts().sort_index().to_dict(), 'division_weight_sum': float(divisions['Basket share'].sum()),
          'item_weight_sum': float(weights['Basket share'].sum()), 'intermediate_tier_weights': 'NOT JOINED', 'sources': sources}
with pd.ExcelWriter(output, engine='xlsxwriter', datetime_format='yyyy-mm') as writer:
    pd.DataFrame({'Read Me': notes}).to_excel(writer, sheet_name='Read Me', index=False)
    meta.to_excel(writer, sheet_name='Series')
    history.to_excel(writer, sheet_name='All CPI levels')
    history.pct_change(12, fill_method=None).mul(100).to_excel(writer, sheet_name='YoY percent')
    history.pct_change(1, fill_method=None).mul(100).to_excel(writer, sheet_name='MoM percent')
    for tier in sorted(meta['Tier'].unique()):
        history[meta.index[meta['Tier'].eq(tier)]].to_excel(writer, sheet_name=f'Tier {tier} levels')
    weights.to_excel(writer, sheet_name='Item weights', index=False)
    divisions.to_excel(writer, sheet_name='Division weights')
    pd.DataFrame(sources).to_excel(writer, sheet_name='Sources', index=False)
    for name, sheet in writer.sheets.items():
        sheet.freeze_panes(1, 1)
        sheet.set_column(0, 0, 20)
        sheet.set_column(1, 750, 14)
    writer.sheets['Read Me'].set_column(0, 0, 130)
    writer.sheets['Series'].set_column(1, 1, 65)
history.to_csv(ROOT / 'monthly_indices.csv', date_format='%Y-%m', encoding='utf-8-sig')
meta.to_csv(ROOT / 'series.csv', encoding='utf-8-sig')
(ROOT / 'history_checks.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
print(output)
print(json.dumps(checks, indent=2))
