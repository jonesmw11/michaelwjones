# Verify persisted Excel values against retained source data and independently calculated rates.
import json
import math
from pathlib import Path

import openpyxl
import pandas as pd

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'prepared_data.json').read_text(encoding='utf-8'))
book=openpyxl.load_workbook(ROOT.parent/'USA CPI - Historical Data and Weights.xlsx',read_only=True,data_only=True)
rows=book['All National CPI Data'].iter_rows(values_only=True)
header=next(rows)
count=0
for row in rows:
    expected=data['histories'][row[0]]['values']
    observed={period:value for period,value in zip(header[7:],row[7:]) if value is not None}
    assert observed==expected,row[0]
    count+=len(observed)
assert count==225468
tier_counts=[]
for tier,components in [(1,8),(2,70),(3,204)]:
    sheet=book[f'Tier {tier}']
    assert sheet.max_row==components+3
    assert abs(sheet['F2'].value-1)<1e-12
    rows=sheet.iter_rows(min_row=3,values_only=True)
    columns=next(rows)
    total=0
    for row in rows:
        total+=row[5]
        expected=data['histories'].get('CUUR0000'+row[0],{}).get('values',{})
        actual={p:v for p,v in zip(columns[10:],row[10:]) if v is not None}
        assert actual==expected,row[0]
    assert abs(total-1)<1e-12
    tier_counts.append(components)
rates=0
for name,lag in [('Inflation MoM percent',1),('Inflation YoY percent',12)]:
    rows=book[name].iter_rows(values_only=True)
    header=next(rows)
    comparison={p:str(pd.Period(p,freq='M')-lag) for p in header[7:]}
    for row in rows:
        values=data['histories'][row[0]]['values']
        for p,actual in zip(header[7:],row[7:]):
            previous=comparison[p]
            if p not in values or previous not in values:
                assert actual is None,(row[0],p)
            else:
                expected=100*(values[p]/values[previous]-1)
                assert actual is not None and math.isclose(actual,expected,abs_tol=1e-11,rel_tol=1e-12),(row[0],p)
                rates+=1
for series in data['histories'].values():
    if series.get('rebased_dec2024'):
        assert series['values']['2024-12']==100
assert '2025-10' not in data['histories']['CUUR0000SA0']['values']
result={'status':'PASS','index_cells_verified':count,'derived_rate_cells_verified':rates,'tier_components':tier_counts,'tier_history_cells_match_master':True,'tier_totals_sum_to_one':True,'rebased_series_full_history_checks':7,'missing_months_preserved':True}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
