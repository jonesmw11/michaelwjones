# Archived core and underlying inflation collection

This inactive collection is retained for provenance. The combined workbook is `../Core Inflation - All Countries.xlsx`; active country copies remain in each country's `Inflation Model` folder. `series_catalog.csv` gives the exact coverage, definitions, sources, seasonal adjustment, units and first/last observations. `observations.csv` is the tidy modelling dataset. Restore this collection to the `macro-work` root before rerunning its scripts.

## Coverage

| Country | Included measures |
|---|---|
| USA | Core CPI and other aggregate CPI exclusions; core PCE, market-based core PCE and other BEA exclusions; Cleveland median CPI, 16% trimmed CPI and median PCE; Dallas trimmed-mean PCE; Atlanta sticky/flexible CPI and their core and shelter-exclusion variants; New York Fed Multivariate Core Trend and uncertainty bands |
| Japan | Statistics Bureau all-items exclusion aggregates, including fresh-food core, fresh-food-and-energy core, and food-excluding-alcohol-and-energy core; BOJ institution-adjusted cores, trimmed mean, weighted median and mode; BOJ quarterly research histories |
| Australia | ABS monthly trimmed mean, weighted median, volatile-item exclusions and other published national analytical exclusion variants; long quarterly ABS/RBA trimmed mean, weighted median and adjusted exclusion histories |
| Korea | The two standard official national cores: excluding food and energy (1990-01–2026-08), and excluding agricultural products and oils (1975-01–2026-08) |

The catalogue contains multiple units, seasonal adjustments and base-specific versions of the same measure. Counts of series variants are not counts of distinct core concepts. This collection covers these official and regularly released underlying measures; it does not claim to catalogue every experimental, discontinued or paper-specific estimator.

## Definitions and treatment

- Percent values use percentage units: 2 means 2%. One-month annualised, multi-month annualised, MoM, QoQ, YoY, index levels and model trends remain distinct.
- Cores overlap and are not a partition of a CPI basket. Their weights should not be added to 1 across measures.
- Official indices are used directly. Derived changes use exact calendar lags without interpolation or forward-filling. Twelve-month median/trimmed CPI rates compound twelve consecutive monthly source changes.
- BOJ monthly base-specific series are retained and also joined as rate histories, prioritising the newest base at overlaps. The underlying base definitions change. Quarterly observations for the latest incomplete quarter may reflect only available months.
- Australia full monthly CPI cores have much shorter history than quarterly cores. The RBA's historical quarterly-collection series are kept separate from the new monthly data and their aggregation basis is documented in the raw RBA Notes sheet.
- US CPI retains the previously accepted provenance: some older BLS history via DBnomics, with recent observations from BLS. Fed, BEA, ABS, RBA and BOJ additions come directly from their publishers.
- Korea was read directly from the public KOSIS rendered tables with all dates selected in ascending order. No API key was required. The agricultural/oil series was extracted in two segments and all seven overlap months match. Counts, sums and order-sensitive weighted checksums verify the transferred data. This completes Korea's **core aggregate histories**, not its still-incomplete detailed CPI component workbook.

## Reproduce

```powershell
python download_sources.py
python build_cores.py
python validate_cores.py
```

Dependencies: pandas, numpy, requests, openpyxl and XlsxWriter. Downloads are cached; `download_manifest.json` records publisher URLs and file hashes. `build_checks.json` records country counts and Korean checks. `validation.json` records full read-back verification across the combined workbook and four country copies.

These scripts build from the saved vintage. The Korea JSON extracts require a new public-table extraction for an update. Existing Japan, Australia, USA CPI and PCE inputs must also be refreshed through their respective pipelines. No unattended monthly updating is claimed.

## Sources

- [KOSIS food-and-energy core](https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1J22009&language=en)
- [KOSIS agricultural-products-and-oils core](https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1J22007&language=en)
- [BOJ core indicators](https://www.boj.or.jp/en/research/research_data/cpi/)
- [ABS CPI](https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/jul-2026)
- [RBA inflation measures](https://www.rba.gov.au/inflation/measures-cpi.html)
- [Cleveland CPI measures](https://www.clevelandfed.org/indicators-and-data/median-cpi)
- [Cleveland median PCE](https://www.clevelandfed.org/indicators-and-data/median-pce-inflation)
- [Dallas trimmed PCE](https://www.dallasfed.org/research/pce)
- [Atlanta sticky-price CPI](https://www.atlantafed.org/research-and-data/data/sticky-price-cpi)
- [New York Fed MCT](https://www.newyorkfed.org/research/policy/mct)
