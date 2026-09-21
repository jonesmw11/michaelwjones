# Assemble national CPI-U histories, derived inflation, and exhaustive weight tiers.
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import xlsxwriter

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT/'prepared_data.json').read_text(encoding='utf-8'))
nodes, histories = data['nodes'], data['histories']
periods = pd.period_range('1913-01', '2026-08', freq='M').astype(str).tolist()
index = pd.DataFrame({sid:s['values'] for sid,s in histories.items()}).reindex(periods)
assert len(index.columns)==400 and int(index.count().sum())==225468
inflation_ids=[sid for sid,s in histories.items() if 'Purchasing power' not in s['name']]
yoy=index[inflation_ids].pct_change(periods=12,fill_method=None)*100
mom=index[inflation_ids].pct_change(periods=1,fill_method=None)*100
out=ROOT.parent/'USA CPI - Historical Data and Weights.xlsx'
checks=[]
with xlsxwriter.Workbook(out) as book:
    book.set_properties({'title':'USA CPI-U historical data and weights','comments':'Official BLS series; pre-2017 history from DBnomics mirror except fully refreshed rebased series. See Guide.'})
    head=book.add_format({'bold':True,'bg_color':'#17365D','font_color':'white','text_wrap':True})
    number=book.add_format({'num_format':'0.000'})
    share=book.add_format({'num_format':'0.0000000000'})
    guide=book.add_worksheet('Guide and Checks')
    notes=[
        'USA | National CPI-U historical data and weights',
        'Scope: U.S. city average, all urban consumers (CPI-U), NOT seasonally adjusted. Includes 400 series, active and discontinued.',
        'History: January 1913 to August 2026 across the dataset; each component starts and ends when its source data is available.',
        'CPI-W, chained CPI, PCE, regional CPI and seasonally adjusted series are outside this workbook scope.',
        'Data are BLS statistics. Pre-2017 observations come from the DBnomics BLS mirror; 2017-2026 observations were refreshed directly from BLS.',
        'Seven series rebased by BLS in May 2026 have their ENTIRE histories refreshed from BLS, on the new December 2024=100 base.',
        'Other index reference bases vary by series. These are native BLS index levels; comparing index levels across components is not meaningful.',
        'Weights: BLS December 2025 relative importance, using 2024 expenditure weights. This is one weight vintage, not historical time-varying weights.',
        'Tier 1: 8 major groups. Tier 2: 70 expenditure classes. Tier 3: 204 finest components supported by the published weight table.',
        'Tier 3 carries 13 unsplit expenditure classes forward. It is not a claim to separately identify all 211 BLS item strata.',
        'All tiers include unsampled categories where applicable. 22 unsampled nodes have weights but no separate published price histories.',
        'Published percentages are retained. Their full-tier sums are 100.000%, 99.999% and 100.001%.',
        'Derived reconciled share = parent reconciled share * child published weight / sum of published sibling weights. Every tier sums to 1.',
        'Reconciliation handles rounding; it does not recover unpublished exact BLS weights or reconstruct official CPI aggregation.',
        'Tier sheets contain index levels. Separate MoM and YoY sheets show derived percentage changes: 100*(index/current comparison index - 1).',
        'Inflation calculations require the exact preceding month or year. Blanks remain blanks; no forward filling or interpolation.',
        'Missing October 2025 observations remain missing. Discontinued series remain in the master with their actual last observation.',
        'Two purchasing-power series appear only in the master; their percentage changes are not labelled inflation.',
        'Do not sum all rows in the master or all rows in the hierarchy: they contain overlapping aggregates.',
        'History mirror: https://db.nomics.world/BLS/cu',
        'Direct refresh: https://api.bls.gov/publicAPI/v2/timeseries/data/',
        'Official weights: https://www.bls.gov/cpi/tables/relative-importance/2025.htm',
        'Official hierarchy: https://www.bls.gov/cpi/additional-resources/cpi-item-aggregation.htm',
        'Rebasing notice: https://www.bls.gov/cpi/notices/2026/rebasing.htm',
    ]
    guide.set_column(0,0,33);guide.set_column(1,5,21)
    for row,note in enumerate(notes):
        guide.merge_range(row,0,row,5,note,book.add_format({'text_wrap':True,'valign':'top'}))
        guide.set_row(row,32 if row else 25)
    guide.write_row(26,0,['Tier','Components','Published total (%)','Reconciled total','Tolerance','Result'],head)

    for sheet_name,frame in [('All National CPI Data',index),('Inflation YoY percent',yoy),('Inflation MoM percent',mom)]:
        sheet=book.add_worksheet(sheet_name)
        sheet.write_row(0,0,['BLS series ID','Item','Item code','Adjustment','Reference base','First observation','Last observation']+periods,head)
        sheet.freeze_panes(1,2);sheet.set_row(0,30)
        sheet.set_column(0,0,23);sheet.set_column(1,1,60);sheet.set_column(2,6,23);sheet.set_column(7,6+len(periods),12,number)
        for row,sid in enumerate(frame.columns,1):
            s=histories[sid]
            vals=frame[sid].dropna()
            basis='Dec 2024=100' if s.get('rebased_dec2024') else ('1967=100 / old base' if s['base_code']=='A' else 'BLS series-specific base')
            if 'Purchasing power' in s['name']:
                basis='BLS purchasing-power units'
            sheet.write_row(row,0,[sid,s['name'],s['item_code'],'Not seasonally adjusted',basis,min(vals.index,default=''),max(vals.index,default='')])
            for col,value in enumerate(frame[sid],7):
                if pd.notna(value):
                    sheet.write_number(row,col,float(value))
        sheet.autofilter(0,0,len(frame.columns),6+len(periods))

    for tier in range(1,4):
        members=[n for n in nodes.values() if n['depth']==tier or (0<n['depth']<tier and not n['children'])]
        sheet=book.add_worksheet(f'Tier {tier}')
        sheet.write(0,0,['','Major groups','Expenditure classes','Finest published weight components'][tier])
        sheet.write(1,0,'Reconciled shares total')
        total=sum(n['share'] for n in members)
        assert abs(total-1)<1e-12
        sheet.write_formula(1,5,f'=SUM(F4:F{len(members)+3})',share,total)
        headers=['Item code','Item','Parent','Weight rank','Published weight (%)','Reconciled basket share','Adjustment from published share','Within-parent share','History status','Source depth']
        sheet.write_row(2,0,headers+periods,head);sheet.set_row(2,44);sheet.freeze_panes(3,2)
        sheet.set_column(0,0,15);sheet.set_column(1,2,42);sheet.set_column(3,9,24);sheet.set_column(10,9+len(periods),12,number)
        rank={n['code']:i+1 for i,n in enumerate(sorted(members,key=lambda n:-n['share']))}
        for row,n in enumerate(members,3):
            parent=nodes[n['parent']]
            sibling_total=sum(nodes[c]['published'] for c in parent['children'])
            sid='CUUR0000'+n['code']
            status='Unsampled: no separate series' if sid not in histories else ('Carried forward unsplit class' if n['depth']<tier else 'Published series')
            sheet.write_row(row,0,[n['code'],n['name'],parent['name'],rank[n['code']],n['published']])
            sheet.write_formula(row,5,f'=E{row+1}/{sibling_total!r}*{parent["share"]!r}',share,n['share'])
            sheet.write_formula(row,6,f'=F{row+1}-E{row+1}/100',share,n['share']-n['published']/100)
            sheet.write_formula(row,7,f'=E{row+1}/{sibling_total!r}',share,n['published']/sibling_total)
            sheet.write_row(row,8,[status,n['depth']])
            if sid in index:
                for col,value in enumerate(index[sid],10):
                    if pd.notna(value):sheet.write_number(row,col,float(value))
        sheet.autofilter(2,0,len(members)+2,9+len(periods))
        published=sum(n['published'] for n in members)
        r=26+tier
        guide.write_row(r,0,[tier,len(members),published])
        guide.write_formula(r,3,f"='Tier {tier}'!F2",share,total)
        guide.write_number(r,4,1e-12)
        guide.write_formula(r,5,f'=IF(ABS(D{r+1}-1)<E{r+1},"PASS","FAIL")',None,'PASS')
        checks.append(dict(tier=tier,components=len(members),published_percent_sum=published,reconciled_sum=total))

    hierarchy=book.add_worksheet('Hierarchy and Weights')
    hierarchy.write_row(0,0,['Code','Item','Depth','Parent code','Published percent','Reconciled share','Children published percent','Published rounding difference','Children reconciled share','Parent-child deviation'],head)
    hierarchy.set_column(0,0,15);hierarchy.set_column(1,1,60);hierarchy.set_column(2,9,23);hierarchy.freeze_panes(1,2)
    for row,n in enumerate(nodes.values(),1):
        childshares=sum(nodes[c]['share'] for c in n['children']) if n['children'] else None
        if childshares is not None:assert abs(childshares-n['share'])<1e-12
        hierarchy.write_row(row,0,[n['code'],n['name'],n['depth'],n['parent'],n['published'],n['share'],n.get('children_published_sum'),n.get('rounding_difference_percent'),childshares,childshares-n['share'] if childshares is not None else None])
    rawweights=book.add_worksheet('Published Weight Table')
    rawweights.write_row(0,0,['Item code','Item','CPI-U percent','CPI-W percent (reference only)'],head)
    for row,n in enumerate(data['all_weights'],1):rawweights.write_row(row,0,[n['code'],n['name'],n['published'],n['published_cpiw']])
    rawweights.set_column(0,0,16);rawweights.set_column(1,1,70);rawweights.set_column(2,3,30);rawweights.freeze_panes(1,2)
    audit=book.add_worksheet('Data Refresh Audit')
    audit.write_row(0,0,['Series','Item','Overlap observations','Changed observations','New observations','API observations 2017-26','Full history rebased refresh'],head)
    for row,r in enumerate(data['refresh_checks'],1):
        s=histories[r['series']]
        audit.write_row(row,0,[r['series'],s['name'],r['overlap_observations'],r['changed_observations'],r['new_observations'],r['bls_observations'],bool(s.get('rebased_dec2024'))])
    audit.set_column(0,0,23);audit.set_column(1,1,65);audit.set_column(2,6,25);audit.freeze_panes(1,2)
    guide.activate()

index.to_csv(ROOT/'national_cpi_indices.csv',index_label='Month')
pd.DataFrame([{k:v for k,v in s.items() if k!='values'} for s in histories.values()]).to_csv(ROOT/'series_catalog.csv',index=False)
(ROOT/'weight_checks.json').write_text(json.dumps(checks,indent=2))
(ROOT/'manifest.json').write_text(json.dumps({'built_utc':datetime.now(timezone.utc).isoformat(),'series':400,'index_observations':int(index.count().sum()),'first_month':periods[0],'last_month':periods[-1],'raw_files':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT/'raw').glob('*.json'))]},indent=2))
print(out)
print(json.dumps(checks))
