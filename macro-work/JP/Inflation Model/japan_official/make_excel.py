# Combine every downloaded official CPI table into one worksheet.
import json
from pathlib import Path

import pandas as pd
import xlsxwriter
from excel_hierarchy import write_hierarchy


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / 'Japan CPI - All Historical Data.xlsx'
manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
tables = []
periods = set()
for entry in manifest:
    stem = f"{entry['frequency']}_{entry['file_id']}"
    frame = pd.read_csv(ROOT / 'processed' / f'{stem}.csv', index_col=0)
    frame.index = frame.index.astype(str)
    metadata = pd.read_csv(ROOT / 'metadata' / f'{stem}.csv', dtype=str).fillna('').set_index('series_code')
    tables.append((entry, frame, metadata))
    periods.update(frame.index)

# Annual columns remain separate from monthly observations.
periods = sorted(periods)
metadata_headers = ['Frequency', 'Measure', 'Adjustment', 'Series code', 'Series name (English)',
                    'Series name (Japanese)', 'Base year', 'Weight per 10000 (2025)',
                    'Raw weight (2025)', 'First available period', 'Last available period',
                    'Observation count', 'Source table', 'Source file ID', 'Source URL']
headers = metadata_headers + periods
period_columns = {period: len(metadata_headers) + i for i, period in enumerate(periods)}
assert len(headers) <= 16384
assert sum(len(frame.columns) for _, frame, _ in tables) + 6 < 1048576

with xlsxwriter.Workbook(OUTPUT, {'constant_memory': True, 'strings_to_formulas': False,
                                 'strings_to_urls': False}) as book:
    sheet = book.add_worksheet('All Japan CPI Data')
    title_format = book.add_format({'bold': True, 'font_size': 17, 'font_color': '#16624C'})
    note_format = book.add_format({'font_color': '#555555', 'font_size': 10})
    header_format = book.add_format({'bold': True, 'bg_color': '#16624C', 'font_color': 'white', 'text_wrap': True})
    value_format = book.add_format({'num_format': '0.0;-0.0;0.0'})
    sheet.write(0, 0, 'Japan CPI | Complete downloaded history', title_format)
    sheet.write(1, 0, '22 official national tables | 2025 base | one row per source-table series; dates across columns.', note_format)
    sheet.write(2, 0, 'Rates are published percentage points (2.5 means 2.5%). YYYY columns are annual averages; YYYY-MM columns are monthly.', note_format)
    sheet.write(3, 0, 'Blank cells are unavailable. Aggregates overlap. Weights are 2025 weights. This is current-classification history, not all retired items.', note_format)
    sheet.write(4, 0, 'Source: Statistics Bureau of Japan / e-Stat. Downloaded 18 September 2026. Original VAR inputs and forecasts remain separate.', note_format)
    sheet.write_row(5, 0, headers, header_format)
    sheet.set_row(5, 42)
    sheet.freeze_panes(6, 5)
    sheet.set_zoom(80)
    sheet.set_column(0, 2, 16)
    sheet.set_column(3, 3, 12)
    sheet.set_column(4, 5, 36)
    sheet.set_column(6, 11, 16)
    sheet.set_column(12, 12, 55)
    sheet.set_column(13, 14, 20, None, {'hidden': True})
    sheet.set_column(len(metadata_headers), len(headers) - 1, 11, value_format)
    output_row = 6
    value_count = 0
    for entry, frame, metadata in tables:
        title = entry['title']
        measure = ('MoM percent' if 'previous month' in title else 'YoY percent'
                   if 'over the year' in title else 'Annual change percent'
                   if 'previous year' in title else 'Index')
        adjustment = 'Seasonally adjusted' if 'Seasonally Adjusted' in title else 'Unadjusted'
        for code in frame.columns:
            meta = metadata.loc[code]
            series = frame[code].dropna()
            fields = [entry['frequency'], measure, adjustment, code, meta.get('name_en', ''),
                      meta.get('name_ja', ''), 2025, meta.get('weight_per_10000', ''),
                      meta.get('weight_raw', ''), series.index[0] if len(series) else '',
                      series.index[-1] if len(series) else '', len(series), title,
                      entry['file_id'], entry['url']]
            for i in (7, 8):
                fields[i] = float(fields[i]) if fields[i] else None
            sheet.write_row(output_row, 0, fields)
            for period, value in series.items():
                sheet.write_number(output_row, period_columns[period], float(value))
            value_count += len(series)
            output_row += 1
    sheet.autofilter(5, 0, output_row - 1, len(headers) - 1)
    sheet.set_tab_color('#16624C')
    book.set_properties({'title': 'Japan CPI - All Historical Data', 'comments': 'All 22 downloaded national e-Stat CPI tables, 2025 base.'})
    write_hierarchy(book)

assert value_count == sum(e['nonmissing_values'] for e in manifest)
print(f'{OUTPUT}\nMaster: {output_row - 6:,} series rows; {len(periods):,} period columns; {value_count:,} numeric observations. Five complete hierarchy tiers and weight checks included.')
