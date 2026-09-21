# Download published central-bank core inflation files without API keys.
import hashlib
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw'
RAW.mkdir(parents=True, exist_ok=True)
sources = {
    'usa_mct.csv': 'https://www.newyorkfed.org/medialibrary/Research/Interactives/Data/mct/mct-chart-data.csv',
    'usa_dallas_history.xlsx': 'https://www.dallasfed.org/~/media/documents/research/pce/pcehist',
    'japan_boj.xlsx': 'https://www.boj.or.jp/en/research/research_data/cpi/cpirev.xlsx',
    'australia_rba.xlsx': 'https://www.rba.gov.au/statistics/tables/xls/g01hist.xlsx',
    'usa_dallas.xlsx': 'https://www.dallasfed.org/-/media/documents/research/pce/pcedata.xlsx',
    'usa_median_pce.csv': 'https://www.clevelandfed.org/-/media/files/webcharts/medianpce/median-pce-full-history.csv',
    'usa_median_cpi.csv': 'https://www.clevelandfed.org/-/media/files/webcharts/mediancpi/mcpi_revised.csv?sc_lang=en',
    'usa_trimmed_cpi.csv': 'https://www.clevelandfed.org/-/media/files/webcharts/mediancpi/trim_revised.csv?sc_lang=en',
    'usa_core_cpi.csv': 'https://www.clevelandfed.org/-/media/files/webcharts/mediancpi/core.csv?sc_lang=en',
    'usa_sticky.xlsx': 'https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/datafiles/research/inflationproject/stickprice/stickyprice.xlsx',
}
manifest = []
for name, url in sources.items():
    path = RAW / name
    if not path.exists():
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        if name.endswith('.xlsx') and not r.content.startswith(b'PK'):
            raise ValueError(f'{name}: not an XLSX')
        path.write_bytes(r.content)
    manifest.append({'file': name, 'url': url, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    print(name, path.stat().st_size, flush=True)
(ROOT / 'download_manifest.json').write_text(json.dumps(manifest, indent=2))
