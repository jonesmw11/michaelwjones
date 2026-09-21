# Build a non-overlapping hierarchy from BLS major-group and expenditure-class codes.
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw'
catalog = json.loads((RAW/'dbnomics_catalog.json').read_text(encoding='utf-8'))
names = catalog['dataset']['dimensions_values_labels']['item']

def normalise(value):
    return re.sub('[^a-z0-9]', '', value.lower())

lookup = {normalise(value):key for key,value in names.items()}
lines = {}
for file in ['weights_web_extract.json', 'weights_web_tail.json']:
    text = json.loads((RAW/file).read_text(encoding='utf-8'))
    for number,name,cu,cw in re.findall(r'L(\d+): (.*?)  \| ([\d.]+)  \| ([\d.]+)', text):
        if 162 <= int(number) <= 455:
            lines[int(number)] = (name,float(cu),float(cw))
assert len(lines) == 294, len(lines)
weights = []
last_code = None
for number,(name,weight,weight_w) in sorted(lines.items()):
    code = lookup.get(normalise(name))
    if code is None:
        assert name.startswith('Unsampled'), name
        assert last_code.startswith('SE'), (name,last_code)
        code = last_code[:4]+'09'
    last_code = code
    weights.append(dict(code=code,name=name,published=weight,published_cpiw=weight_w,source_line=number))
assert len({n['code'] for n in weights}) == len(weights)
all_weights = {n['code']:n for n in weights}
nodes = {}
for n in weights:
    code = n['code']
    if code == 'SA0':
        depth,parent=0,None
    elif code in ['SAA','SAE','SAF','SAH','SAM','SAG','SAR','SAT']:
        depth,parent=1,'SA0'
    elif code.startswith('SE') and len(code)==4:
        depth,parent=2,'SA'+code[2]
    elif code.startswith('SE') and len(code)==6:
        depth,parent=3,code[:4]
    else:
        continue
    nodes[code] = dict(**n,depth=depth,parent=parent,children=[])
for code,n in nodes.items():
    if n['parent']:
        nodes[n['parent']]['children'].append(code)
nodes['SA0']['share']=1.
for n in nodes.values():
    if n['children']:
        total = sum(nodes[c]['published'] for c in n['children'])
        assert abs(total-n['published']) < .01, (n['code'],total,n['published'])
        for code in n['children']:
            nodes[code]['share'] = n['share']*nodes[code]['published']/total
        n['children_published_sum'] = total
        n['rounding_difference_percent'] = total-n['published']

histories = {}
for path in sorted(RAW.glob('history_*.json')):
    data=json.loads(path.read_text(encoding='utf-8'))
    for series in data['series']['docs']:
        values={p:float(v) for p,v in zip(series['period'],series['value']) if isinstance(v,(int,float))}
        histories[series['series_code']] = dict(code=series['series_code'],item_code=series['dimensions']['item'],name=names[series['dimensions']['item']],base_code=series['dimensions']['base'],values=values,api_refreshed=False)
refresh_checks=[]
footnotes=[]
for path in sorted(RAW.glob('bls_refresh_*.json')):
    data=json.loads(path.read_text(encoding='utf-8'))
    returned={s['seriesID'] for s in data['Results']['series']}
    assert returned==set(data['request_series'])
    for series in data['Results']['series']:
        record=histories[series['seriesID']]
        latest={}
        for observation in series['data']:
            period=observation['period']
            if period.startswith('M') and 1<=int(period[1:])<=12:
                key=observation['year']+'-'+period[1:]
                try:
                    latest[key]=float(observation['value'])
                except ValueError:
                    continue
                if any(observation['footnotes']):
                    footnotes.append(dict(series=record['code'],period=key,footnotes=observation['footnotes']))
        overlap=set(latest)&set(record['values'])
        changes=sum(latest[p]!=record['values'][p] for p in overlap)
        refresh_checks.append(dict(series=record['code'],overlap_observations=len(overlap),changed_observations=changes,new_observations=len(set(latest)-set(record['values'])),bls_observations=len(latest),messages=data.get('message',[])))
        # Replace the complete requested window, retaining genuine missing observations as blanks.
        record['values']={p:v for p,v in record['values'].items() if p<'2017-01'}
        record['values'].update(latest)
        record['api_refreshed']=bool(latest)

rebased_ids={r['series'] for r in refresh_checks if r['changed_observations']}
rebased_values={sid:{} for sid in rebased_ids}
for path in sorted(RAW.glob('bls_rebased_*.json')):
    result=json.loads(path.read_text(encoding='utf-8'))
    for series in result['Results']['series']:
        for observation in series['data']:
            period=observation['period']
            if period.startswith('M') and 1<=int(period[1:])<=12:
                rebased_values[series['seriesID']][observation['year']+'-'+period[1:]]=float(observation['value'])
for sid,values in rebased_values.items():
    old_periods={p for p in histories[sid]['values'] if p<'2017-01'}
    assert old_periods <= set(values), (sid,'Incomplete rebased history')
    histories[sid]['values']={p:v for p,v in histories[sid]['values'].items() if p>='2017-01'}
    histories[sid]['values'].update(values)
    histories[sid]['rebased_dec2024']=True

for tier in range(1,4):
    members=[n for n in nodes.values() if n['depth']==tier or (0<n['depth']<tier and not n['children'])]
    assert abs(sum(n['share'] for n in members)-1)<1e-12
    print('Tier',tier,'components',len(members),'published sum',sum(n['published'] for n in members),'share sum',sum(n['share'] for n in members))
print('Series',len(histories),'observations',sum(len(s['values']) for s in histories.values()))
print('Unpublished basket nodes',[n['name'] for n in nodes.values() if 'CUUR0000'+n['code'] not in histories])
(ROOT/'prepared_data.json').write_text(json.dumps(dict(nodes=nodes,histories=histories,all_weights=weights,refresh_checks=refresh_checks,footnotes=footnotes)),encoding='utf-8')
pd.DataFrame([{k:v for k,v in n.items() if k!='children'} for n in nodes.values()]).to_csv(ROOT/'hierarchy_weights.csv',index=False)
