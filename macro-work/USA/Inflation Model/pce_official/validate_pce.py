# Read the delivered workbook back and compare its data with the saved machine-readable output.
import json
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent
path = ROOT.parent / 'USA PCE - Historical Data and Weights.xlsx'
book = openpyxl.load_workbook(path, read_only=True, data_only=True)
prices = pd.read_csv(ROOT / 'monthly_prices.csv', index_col=0, parse_dates=True)
spending = pd.read_csv(ROOT / 'monthly_spending.csv', index_col=0, parse_dates=True)
count = 0
for sheet, expected in [('All monthly prices', prices), ('All monthly spending', spending),
                        ('MoM percent', prices.pct_change(1, fill_method=None)*100),
                        ('YoY percent', prices.pct_change(12, fill_method=None)*100)]:
    rows = list(book[sheet].values)
    actual = pd.DataFrame([r[1:] for r in rows[1:]], index=pd.DatetimeIndex([r[0] for r in rows[1:]]),
                          columns=[str(c).split(' | ')[0] for c in rows[0][1:]], dtype=float)
    assert actual.index.equals(expected.index)
    assert list(actual.columns) == list(expected.columns)
    np.testing.assert_allclose(actual, expected, equal_nan=True, rtol=1e-12, atol=1e-12)
    count += int(actual.notna().sum().sum())
tiers = []
for name in book.sheetnames:
    if name.startswith('Tier ') and name.endswith(' weights'):
        rows = list(book[name].values)
        values = np.array([[np.nan if v is None else v for v in r[1:-1]] for r in rows[1:]], dtype=float)
        totals = values.sum(axis=1)
        complete = np.isfinite(totals)
        np.testing.assert_allclose(totals[complete], 1, rtol=0, atol=1e-12)
        assert complete[-1]
        saved = np.array([np.nan if r[-1] is None else r[-1] for r in rows[1:]])
        np.testing.assert_allclose(saved, totals, equal_nan=True, rtol=0, atol=1e-12)
        tiers.append({'sheet': name, 'components': values.shape[1], 'complete_months': int(complete.sum()), 'latest_sum': float(totals[-1])})
report = {'status': 'PASS', 'checked_numeric_values': count, 'tier_checks': tiers, 'workbook_bytes': path.stat().st_size}
(ROOT / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
book.close()
print(json.dumps(report, indent=2))
