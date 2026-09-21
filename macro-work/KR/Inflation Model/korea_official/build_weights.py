# Official Korean CPI weights; historical export remains pending.
import json
from pathlib import Path

import openpyxl
import pandas as pd
import xlsxwriter

ROOT = Path(__file__).resolve().parent
source = openpyxl.load_workbook(ROOT / 'raw/weights_2022.xlsx', data_only=True)
items = pd.DataFrame(list(source.worksheets[0].values)[3:], columns=['Unused', 'Division', 'Item', 'Published weight per 1000']).drop(columns='Unused')
items['Basket share'] = items['Published weight per 1000'] / 1000
groups = items.groupby('Division', sort=False)['Published weight per 1000'].sum().reset_index()
groups['Basket share'] = groups['Published weight per 1000'] / 1000
items['Within-division share'] = items['Published weight per 1000'] / items.groupby('Division')['Published weight per 1000'].transform('sum')
assert len(items) == 458 and len(groups) == 12
assert abs(items['Basket share'].sum()-1) < 1e-12
assert abs(groups['Basket share'].sum()-1) < 1e-12
assert all(abs(v-1) < 1e-12 for v in items.groupby('Division')['Within-division share'].sum())
out = ROOT.parent / 'Korea CPI - Official Weights.xlsx'
with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
    book = writer.book
    guide = book.add_worksheet('Read Me')
    notes = [
        'Korea CPI | Official 2022 basket weights | PARTIAL DELIVERY',
        'Historical index data and intermediate classification tiers are NOT included: KOSIS download access was blocked.',
        'Index base is 2020=100; weight reference year is 2022, applied from January 2022.',
        'The source contains 12 expenditure divisions and 458 representative items.',
        'Item shares are the published weights divided by 1000; they sum to 1 without reconciliation.',
        'Division weights are sums of their published constituent item weights.',
        'These are current basket weights, not time-varying historical weights.',
        'Source: https://www.mods.go.kr/twcp/file/cpi_dl_2022.xlsx',
        'Methodology: https://www.mods.go.kr/menu.es?mid=b70101040000',
        'Historical table: https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1J22001&language=en',
    ]
    for row, note in enumerate(notes):
        guide.write(row, 0, note)
    guide.set_column(0, 0, 120)
    share_format = book.add_format({'num_format': '0.0000000000'})
    for name, frame in [('Divisions', groups), ('Detailed Items', items)]:
        frame.to_excel(writer, sheet_name=name, index=False, startrow=2)
        sheet = writer.sheets[name]
        sheet.freeze_panes(3, 2)
        sheet.set_column(0, len(frame.columns)-1, 28)
        sheet.autofilter(2, 0, len(frame)+2, len(frame.columns)-1)
        col = frame.columns.get_loc('Basket share')
        letter = xlsxwriter.utility.xl_col_to_name(col)
        sheet.write(0, 0, 'Basket shares sum to 1')
        sheet.write_formula(0, col, f'=SUM({letter}4:{letter}{len(frame)+3})', share_format, 1.)
        sheet.set_column(col, col, 25, share_format)
    guide.activate()
items.to_csv(ROOT / 'item_weights.csv', index=False, encoding='utf-8-sig')
groups.to_csv(ROOT / 'division_weights.csv', index=False, encoding='utf-8-sig')
(ROOT / 'weight_checks.json').write_text(json.dumps({'divisions':12, 'items':458, 'division_share_sum':float(groups['Basket share'].sum()), 'item_share_sum':float(items['Basket share'].sum()), 'history_status':'BLOCKED: KOSIS export download rejected; not included'}, indent=2))
print(out)
