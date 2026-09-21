# Download full national NSA CPI-U history from the public BLS mirror, then refresh through the BLS API.
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw'
RAW.mkdir(exist_ok=True)
catalog = json.loads((RAW / 'dbnomics_catalog.json').read_text())
series = [s for s in catalog['series']['docs'] if s['dimensions']['seasonal'] == 'U']
for offset in range(0, len(series), 100):
    path = RAW / f'history_{offset:03}.json'
    if not path.exists():
        response = requests.get('https://api.db.nomics.world/v22/series/BLS/cu', params={'dimensions': json.dumps({'area':['0000'], 'periodicity':['R'], 'seasonal':['U']}), 'limit':100, 'offset':offset, 'observations':1}, timeout=120)
        response.raise_for_status()
        result = response.json()
        assert result['series']['num_found'] == len(series)
        path.write_text(json.dumps(result), encoding='utf-8')
    print('Historical batch', offset, flush=True)

# Sixteen batches fit the documented unregistered limit of 25 daily requests.
for offset in range(0, len(series), 25):
    path = RAW / f'bls_refresh_{offset:03}.json'
    if not path.exists():
        ids = [s['series_code'] for s in series[offset:offset+25]]
        response = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', json={'seriesid':ids, 'startyear':'2017', 'endyear':'2026'}, timeout=120)
        response.raise_for_status()
        result = response.json()
        if result['status'] != 'REQUEST_SUCCEEDED':
            raise RuntimeError(result.get('message'))
        path.write_text(json.dumps({'retrieved_utc':datetime.now(timezone.utc).isoformat(), 'request_series':ids, **result}), encoding='utf-8')
    print('BLS refresh batch', offset, flush=True)

# BLS rebased these seven national NSA series in May 2026. Refresh their full
# histories to avoid joining old and new reference bases at January 2017.
rebased = ['SEEB02','SEEE','SEEE04','SEGA','SEMD','SERA01','SERA03']
for start in range(1947, 2017, 10):
    path = RAW / f'bls_rebased_{start}.json'
    if not path.exists():
        ids = ['CUUR0000'+item for item in rebased]
        response = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', json={'seriesid':ids, 'startyear':str(start), 'endyear':str(start+9)}, timeout=120)
        response.raise_for_status()
        result = response.json()
        if result['status'] != 'REQUEST_SUCCEEDED':
            raise RuntimeError(result.get('message'))
        path.write_text(json.dumps({'retrieved_utc':datetime.now(timezone.utc).isoformat(), 'request_series':ids, **result}), encoding='utf-8')
    print('Rebased history', start, flush=True)
