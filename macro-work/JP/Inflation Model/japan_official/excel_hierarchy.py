# Build complete CPI basket tiers from the indentation in the official item list.
import hashlib
import json
from pathlib import Path

import openpyxl
import pandas as pd
import requests
from xlsxwriter.utility import xl_rowcol_to_cell


ROOT = Path(__file__).resolve().parent
SOURCE_URL = 'https://www.stat.go.jp/english/data/cpi/zuhyou/2025base-list.xlsx'


def write_hierarchy(book):
    source = ROOT / 'raw/2025base-list.xlsx'
    if not source.exists():
        response = requests.get(SOURCE_URL, timeout=60)
        response.raise_for_status()
        source.write_bytes(response.content)
    official = openpyxl.load_workbook(source, data_only=True)['List']
    nodes = {}
    stack = []
    for row in list(official.values)[3:]:
        code = row[7] or row[8]
        # Fresh food begins the overlapping supplementary aggregates.
        if code == '0157':
            break
        if not code:
            continue
        column = next(i for i, value in enumerate(row[:7]) if value is not None)
        if code == '0001':
            parent, depth = None, 0
            stack = [(-1, code)]
        else:
            while stack[-1][0] >= column:
                stack.pop()
            parent = stack[-1][1]
            depth = nodes[parent]['depth'] + 1
            stack.append((column, code))
        nodes[code] = dict(code=code, name=row[column], parent=parent, depth=depth,
                           raw_weight=int(row[10]), rounded_weight=row[11], children=[],
                           official_type='Group' if row[7] else 'Item')
        if parent:
            nodes[parent]['children'].append(code)
    total = nodes['0001']['raw_weight']
    for node in nodes.values():
        if node['children']:
            assert sum(nodes[c]['raw_weight'] for c in node['children']) == node['raw_weight'], node['code']
    leaves = [c for c, n in nodes.items() if not n['children']]
    assert len(leaves) == 589
    assert sum(nodes[c]['raw_weight'] for c in leaves) == total
    catalog = pd.read_csv(ROOT / 'metadata/series_catalog.csv', dtype=str).fillna('').set_index('series_code')
    for code, node in nodes.items():
        assert int(catalog.loc[code, 'weight_raw']) == node['raw_weight']
    header = book.add_format({'bold': True, 'bg_color': '#16624C', 'font_color': 'white', 'text_wrap': True})
    weight_format = book.add_format({'num_format': '0.0000000000'})
    number_format = book.add_format({'num_format': '0.0'})
    good = book.add_format({'bg_color': '#E0F1E8', 'font_color': '#16624C'})
    notes = book.add_worksheet('Guide and Weight Checks')
    instructions = [
        'Japan CPI hierarchy and weight checks | 2025 basket',
        'Each Tier sheet is a complete, non-overlapping national basket. Its Basket weight column sums to 1.',
        'Weights = official unrounded national weight / official all-items weight. No forced rescaling or balancing residual.',
        'The official tree is uneven: each tier expands one parent-child step; terminal items are carried forward.',
        'Tier 1 = 10 major groups. Tier 5 = all 589 detailed items. Tier numbers describe tree depth, not official named classifications.',
        'Carried leaf rows retain their official shallower depth. They are not invented subcategories.',
        'All Japan CPI Data preserves all 22 tables, including overlapping aggregates. Never sum weights across that master sheet.',
        'Hierarchy has all 735 basic-tree nodes. Its total column must NOT be summed across levels; parent shares sum to 1 within siblings.',
        'Tier sheets include monthly indices, MoM/YoY rates, and annual indices/annual changes. Blank = unavailable; 2.5 means 2.5%.',
        'These are 2025 basket weights, not historical time-varying weights. Do not use them as historical contemporaneous weights.',
        'Weight source: ' + SOURCE_URL,
        'Source rounded weights per 10000 are retained for reference; rounding can prevent those from summing to exactly 10000.',
    ]
    for i, line in enumerate(instructions):
        notes.write(i, 0, line)
    notes.set_column(0, 0, 38)
    notes.set_column(1, 6, 22)
    notes.write_row(14, 0, ['Tier', 'Series count', 'Raw weight sum', 'Basket weight sum', 'Deviation from 1', 'Check', 'Carried leaves'], header)

    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    panels = []
    for entry in manifest:
        if not entry['title'].startswith('Indices of Items'):
            continue
        title = entry['title']
        measure = 'MoM %' if 'previous month' in title else 'YoY %' if 'over the year' in title else 'Annual change %' if 'previous year' in title else 'Index'
        frame = pd.read_csv(ROOT / 'processed' / f"{entry['frequency']}_{entry['file_id']}.csv", index_col=0)
        panels.append((entry['frequency'] + ' ' + measure, frame))
    tier_metadata = ['Code', 'Name (English)', 'Name (Japanese)', 'Official tree depth', 'Parent code',
                     'Carried terminal item', 'Official raw weight', 'Basket weight (sum = 1)',
                     'Published weight per 10000', 'Weight rank within tier']
    series_headers = [f'{label} | {period}' for label, frame in panels for period in frame.index]
    frontier = ['0001']
    audit = []
    for tier in range(1, max(n['depth'] for n in nodes.values()) + 1):
        frontier = [child for code in frontier for child in (nodes[code]['children'] or [code])]
        assert sum(nodes[c]['raw_weight'] for c in frontier) == total
        name = f'Tier {tier}'
        sheet = book.add_worksheet(name)
        sheet.write(0, 0, f'{name}: complete basket; 2025 weights; {len(frontier)} series')
        sheet.write(1, 0, 'SUM of basket weights')
        end_row = len(frontier) + 3
        sheet.write_formula(1, 7, f'=SUM(H4:H{end_row})', weight_format, 1.0)
        sheet.write_row(2, 0, tier_metadata + series_headers, header)
        sheet.set_row(2, 45)
        sheet.freeze_panes(3, 2)
        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 2, 36)
        sheet.set_column(3, 9, 18)
        sheet.set_column(10, 10 + len(series_headers) - 1, 15, number_format)
        sheet.set_zoom(80)
        ranks = pd.Series({c: nodes[c]['raw_weight'] for c in frontier}).rank(method='min', ascending=False)
        for rownum, code in enumerate(frontier, 3):
            node = nodes[code]
            carried = node['depth'] < tier
            fields = [code, node['name'], catalog.loc[code, 'name_ja'], node['depth'], node['parent'],
                      'Yes' if carried else 'No', node['raw_weight'], None,
                      node['rounded_weight'], int(ranks[code])]
            sheet.write_row(rownum, 0, fields)
            sheet.write_formula(rownum, 7, f'=G{rownum+1}/{total}', weight_format, node['raw_weight']/total)
            col = 10
            for _, frame in panels:
                values = frame[code]
                for value in values:
                    if pd.notna(value):
                        sheet.write_number(rownum, col, float(value))
                    col += 1
        sheet.autofilter(2, 0, end_row-1, 9 + len(series_headers))
        carried_count = sum(nodes[c]['depth'] < tier for c in frontier)
        checkrow = 14 + tier
        notes.write_row(checkrow, 0, [name, len(frontier), total])
        notes.write_formula(checkrow, 3, f"='{name}'!H2", weight_format, 1.0)
        notes.write_formula(checkrow, 4, f'=D{checkrow+1}-1', weight_format, 0.0)
        notes.write_formula(checkrow, 5, f'=IF(ABS(E{checkrow+1})<1E-12,"PASS","FAIL")', good, 'PASS')
        notes.write(checkrow, 6, carried_count)
        audit.append(dict(tier=tier, series=len(frontier), raw_weight_sum=total, weight_sum=sum(nodes[c]['raw_weight']/total for c in frontier), carried_leaves=carried_count))

    hierarchy = book.add_worksheet('Official Hierarchy')
    hierarchy.write_row(0, 0, ['Code', 'Name', 'Depth', 'Parent', 'Type', 'Raw weight', 'Basket share',
                              'Share of parent', 'Children raw sum', 'Children minus parent', 'Check'], header)
    hierarchy.freeze_panes(1, 2)
    hierarchy.set_column(0, 0, 12)
    hierarchy.set_column(1, 1, 45)
    hierarchy.set_column(2, 10, 20)
    rowmap = {code: i+1 for i, code in enumerate(nodes)}
    for code, node in nodes.items():
        rownum = rowmap[code]
        parent_weight = nodes[node['parent']]['raw_weight'] if node['parent'] else total
        hierarchy.write_row(rownum, 0, [code, node['name'], node['depth'], node['parent'], node['official_type'], node['raw_weight']])
        hierarchy.write_formula(rownum, 6, f'=F{rownum+1}/{total}', weight_format, node['raw_weight']/total)
        parent_cell = f'F{rowmap[node["parent"]]+1}' if node['parent'] else f'F{rownum+1}'
        hierarchy.write_formula(rownum, 7, f'=F{rownum+1}/{parent_cell}', weight_format, node['raw_weight']/parent_weight)
        if node['children']:
            refs = ','.join(xl_rowcol_to_cell(rowmap[c],5) for c in node['children'])
            hierarchy.write_formula(rownum, 8, f'=SUM({refs})', None, node['raw_weight'])
            hierarchy.write_formula(rownum, 9, f'=I{rownum+1}-F{rownum+1}', None, 0)
            hierarchy.write_formula(rownum, 10, f'=IF(J{rownum+1}=0,"PASS","FAIL")', good, 'PASS')
    hierarchy.autofilter(0, 0, len(nodes), 10)
    notes.write(22, 0, f'All {sum(bool(n["children"]) for n in nodes.values())} parent-child raw-weight reconciliations PASS exactly.')
    notes.write(23, 0, f'589 leaf weights sum exactly to the root raw weight of {total:,}.')
    notes.activate()
    (ROOT / 'metadata/hierarchy_weight_checks.json').write_text(json.dumps(dict(source_url=SOURCE_URL,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), root_weight=total, leaf_count=len(leaves),
        parent_checks_passed=sum(bool(n['children']) for n in nodes.values()), tiers=audit), indent=2), encoding='utf-8')
    pd.DataFrame([{k:v for k,v in node.items() if k != 'children'} for node in nodes.values()]).to_csv(ROOT/'metadata/official_hierarchy.csv',index=False,encoding='utf-8-sig')
    print('Hierarchy validated:', audit, flush=True)
