# Official Australian CPI workbook

`../Australia CPI - All Historical Data.xlsx` contains 1,858 national series and 103,352 numeric observations from ABS tables 1–9 and 17–18, from 1948 Q3 where available. Monthly observations run through July 2026 and quarterly observations through 2026 Q2. Coverage differs by series; blanks are unavailable observations. National CPI means the weighted average of eight capital cities.

Three exhaustive tier sheets contain 11 groups, 33 subgroups and 87 expenditure classes. Published 2025 weights sum to 100.00%, 100.01% and 99.96% because of rounding. Published weights remain visible. Derived shares reconcile each sibling set to its parent, so each full tier sums to 1 and child shares equal parent shares. They are not claimed to be unpublished official exact weights. These weights are not historical basket vintages.

The master also includes overlapping analytical series; do not add every master row together. Monthly and quarterly observations are separate and no histories are artificially spliced.

Run `python build_workbook.py` with pandas, requests, openpyxl and XlsxWriter. Download URLs and SHA-256 hashes are in `manifest.json`; the release is pinned to July 2026. Raw files are retained. `weight_checks.json` records the checks. Workbook readback verified all 103,352 numeric master observations are present and all tier totals equal 1.

Official source: https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/jul-2026/
