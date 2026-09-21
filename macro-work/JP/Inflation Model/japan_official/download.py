import argparse
import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parent
BASE = 'https://www.e-stat.go.jp'
CATALOG = BASE + '/en/stat-search/files?tstat=000001243876&toukei=00200573&cycle=0&tclass1=000001243880&tclass2=000001243881&tclass3=000001243883&layout=datalist&page=1&tclass5val=0&tclass4='
CATALOGS = {'monthly': CATALOG + '000001243886', 'annual': CATALOG + '000001243890'}
SESSION = requests.Session()
SESSION.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))


def get(url, **kwargs):
    response = SESSION.get(url, timeout=60, **kwargs)
    response.raise_for_status()
    return response


def parse_file(content, frequency, file_id):
    # e-Stat exports include several metadata rows before the observations.
    try:
        source = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        source = content.decode('cp932')
    rows = list(csv.reader(io.StringIO(source)))
    for row in rows:
        if row:
            row[0] = row[0].strip()
    start = next(i for i, row in enumerate(rows) if row and row[0].isdigit() and len(row[0]) in (4, 6))
    headers = rows[:start]
    code_row = next(row for row in headers if 'Group/Item code' in row[0])
    codes = code_row[1:]
    if len(codes) != len(set(codes)):
        raise ValueError(f'Duplicate component codes in {file_id}')
    metadata = pd.DataFrame({'series_code': codes})
    for label, name in [('Group/Item', 'name_en'), ('類・品目', 'name_ja'), ('Serial number', 'serial_number'), ('Weight per 10000', 'weight_per_10000'), ('ウエイト(Weight)', 'weight_raw')]:
        candidates = [row for row in headers if (row[0] == label if label in ('Group/Item', '類・品目') else label in row[0])]
        if candidates:
            metadata[name] = candidates[0][1:]
    observations = [row for row in rows[start:] if row and row[0].isdigit() and len(row[0]) in (4, 6)]
    frame = pd.DataFrame([row[1:] for row in observations], columns=codes)
    frame.index = pd.Index([row[0] for row in observations], name='period')
    if frame.index.has_duplicates:
        raise ValueError(f'Duplicate periods in {file_id}')
    numeric = frame.apply(pd.to_numeric, errors='coerce')
    markers = sorted(set(frame.where(numeric.isna()).stack().astype(str)) - {''})
    # Preserve source missing values; never interpolate or forward-fill.
    coverage = pd.DataFrame({
        'series_code': codes,
        'first_period': [numeric[c].first_valid_index() for c in codes],
        'last_period': [numeric[c].last_valid_index() for c in codes],
        'observations': numeric.notna().sum().values,
        'missing_periods': numeric.isna().sum().values,
    })
    metadata = metadata.merge(coverage, on='series_code', validate='one_to_one')
    metadata['source_file_id'] = file_id
    metadata['base_year'] = 2025
    if frequency == 'monthly':
        periods = pd.PeriodIndex(numeric.index, freq='M')
        if not periods.equals(pd.period_range(periods.min(), periods.max(), freq='M')):
            raise ValueError(f'Missing or unordered monthly rows in {file_id}')
        numeric.index = periods.astype(str)
        numeric.index.name = 'date'
    return numeric, metadata, markers


def download_files():
    manifest = []
    for frequency, catalog_url in CATALOGS.items():
        catalog = get(catalog_url)
        (ROOT / 'raw' / f'catalog_{frequency}.html').write_bytes(catalog.content)
        soup = BeautifulSoup(catalog.content, 'html.parser')
        links = soup.select('a[data-file_type="CSV"]')
        expected = 14 if frequency == 'monthly' else 8
        if len(links) != expected:
            raise ValueError(f'Expected {expected} {frequency} files, found {len(links)}; review catalog changes')
        for link in links:
            url = urljoin(BASE, link['href'])
            file_id = parse_qs(urlparse(url).query)['statInfId'][0]
            parent = link.find_parent('li', class_='stat-dataset_list-detail-item')
            title = parent.get_text(' ', strip=True).split('Survey date')[0].strip()
            stem = frequency + '_' + file_id
            raw_path = ROOT / 'raw' / (stem + '.csv')
            content = raw_path.read_bytes() if raw_path.exists() and ARGS.cached else get(url).content
            if b'<html' in content[:500].lower():
                raise ValueError(f'HTML returned for {file_id}')
            (ROOT / 'raw' / (stem + '.csv')).write_bytes(content)
            frame, metadata, markers = parse_file(content, frequency, file_id)
            frame.to_csv(ROOT / 'processed' / (stem + '.csv'), encoding='utf-8-sig')
            metadata.to_csv(ROOT / 'metadata' / (stem + '.csv'), index=False, encoding='utf-8-sig')
            entry = dict(file_id=file_id, frequency=frequency, title=title, url=url,
                         catalog_url=catalog_url, base_year=2025, rows=len(frame), series=len(frame.columns),
                         first_period=str(frame.index.min()), last_period=str(frame.index.max()),
                         nonmissing_values=int(frame.notna().sum().sum()), missing_markers=markers,
                         sha256=hashlib.sha256(content).hexdigest(), retrieved_utc=datetime.now(timezone.utc).isoformat())
            manifest.append(entry)
            print(f'{frequency}: {title}: {frame.shape}', flush=True)
            if frequency == 'monthly' and title.startswith('Indices of Items'):
                measure = 'mom_percent' if 'previous month' in title else 'yoy_percent' if 'over the year' in title else 'index'
                frame.to_csv(ROOT / 'processed' / f'japan_cpi_{measure}.csv', encoding='utf-8-sig')
                if measure == 'index':
                    metadata.to_csv(ROOT / 'metadata' / 'series_catalog.csv', index=False, encoding='utf-8-sig')
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    pd.DataFrame(manifest).to_csv(ROOT / 'metadata' / 'table_catalog.csv', index=False, encoding='utf-8-sig')


def download_api():
    # Optional authenticated API export; kept separate from the published CSV exports.
    key = os.getenv('ESTAT_APP_ID') or os.getenv('ESTAT_API_KEY')
    if not key:
        raise SystemExit('Set ESTAT_APP_ID or ESTAT_API_KEY locally to use --api.')
    endpoint = 'https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData'
    params = dict(appId=key, statsDataId='0004052037', lang='E', cdArea='00000', limit=100000)
    position = 1
    while position:
        params['startPosition'] = position
        # Do not print URLs or exception details containing the application ID.
        try:
            payload = get(endpoint, params=params).json()
        except Exception:
            raise RuntimeError('API request failed; verify connectivity and credentials locally.') from None
        result = payload['GET_STATS_DATA']
        if int(result['RESULT']['STATUS']) != 0:
            raise RuntimeError('e-Stat API returned nonzero status ' + str(result['RESULT']['STATUS']))
        safe_payload = json.dumps(payload, ensure_ascii=False).replace(key, '[REDACTED]')
        (ROOT / 'raw' / f'api_{position:09d}.json').write_text(safe_payload, encoding='utf-8')
        info = result['STATISTICAL_DATA']['RESULT_INF']
        next_position = int(info.get('NEXT_KEY', 0))
        if next_position and next_position <= position:
            raise RuntimeError('API pagination did not advance')
        print(f'Saved API page starting at {position}', flush=True)
        position = next_position


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', action='store_true', help='Download raw national API pages using a locally configured application ID')
    parser.add_argument('--cached', action='store_true', help='Reuse existing raw CSV files for processing')
    ARGS = parser.parse_args()
    for folder in ['raw', 'processed', 'metadata']:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    download_api() if ARGS.api else download_files()
