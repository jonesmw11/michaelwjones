# Verify every saved workbook observation against the assembled long-form dataset.
import json
from pathlib import Path
import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent
meta = pd.read_csv(ROOT / 'series_catalog.csv').set_index('id')
long = pd.read_csv(ROOT / 'observations.csv', dtype={'Period': str})
assert not long.duplicated(['id', 'Period']).any()
assert set(meta.index) == set(long.id)
paths = [ROOT.parent / 'Core Inflation - All Countries.xlsx']
paths += [
    ROOT.parent / 'USA Inflation Model' / 'USA - Core Inflation Measures.xlsx',
    ROOT.parent / 'AU Inflation Model' / 'Australia - Core Inflation Measures.xlsx',
    ROOT.parent / 'KR Inflation Model' / 'Korea - Core Inflation Measures.xlsx',
    ROOT.parent / 'JP Inflation Model' / 'Japan - Core Inflation Measures.xlsx',
]
checked = 0
for path in paths:
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ids = []
    for sheet in book:
        if sheet.title in ['Guide', 'Series']:
            continue
        rows = list(sheet.values)
        columns = [s.split(' | ')[0] for s in rows[0][1:]]
        periods = [str(r[0]) for r in rows[1:]]
        actual = pd.DataFrame([r[1:] for r in rows[1:]], index=periods, columns=columns, dtype=float)
        expected = long[long.id.isin(columns)].pivot(index='Period', columns='id', values='Value').reindex(index=periods, columns=columns)
        np.testing.assert_allclose(actual, expected, equal_nan=True, atol=1e-10, rtol=1e-12)
        checked += int(actual.notna().sum().sum())
        ids.extend(columns)
    assert len(ids) == len(set(ids))
    book.close()
assert (meta.groupby('country').size() > 0).all()
for name, expected in [('CPI excluding food and energy', 440), ('CPI excluding agricultural products and oils', 620)]:
    row = meta[(meta.country == 'Korea') & (meta.name == name) & meta.unit.str.startswith('Index')].iloc[0]
    assert row.observations == expected and row.last_period == '2026-08'
report = {'status': 'PASS', 'workbooks': len(paths), 'unique_series_variants': len(meta),
          'unique_observations': len(long), 'workbook_numeric_values_checked': checked,
          'country_variant_counts': meta.groupby('country').size().to_dict()}
(ROOT / 'validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
