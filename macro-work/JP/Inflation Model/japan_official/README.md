# Japan official CPI history

[Core and underlying inflation histories](../Japan%20-%20Core%20Inflation%20Measures.xlsx) combine the national exclusion-based cores with BOJ trimmed-mean, weighted-median, mode and institution-adjusted estimates. The shared cross-country construction pipeline is retained in the top-level archive.

Downloaded 18 September 2026 from the Statistics Bureau of Japan, Ministry of Internal Affairs and Communications, through e-Stat. These are national Japan series, not Tokyo or individual cities.

## Main files

- `../Japan CPI - All Historical Data.xlsx`: a master sheet of all 22 downloaded tables, five complete basket tiers with history and weights, an official parent-child hierarchy sheet, and weight checks. Build with `python make_excel.py`.
- `raw/2025base-list.xlsx`: the official Statistics Bureau item classification and weight workbook, downloaded from https://www.stat.go.jp/english/data/cpi/zuhyou/2025base-list.xlsx.
- `metadata/official_hierarchy.csv` and `metadata/hierarchy_weight_checks.json`: hierarchy, source checksum and weight reconciliation results.

Tier weights use the official unrounded national weights divided by the official all-items weight (3,543,757,090). Every parent equals the sum of its direct children exactly in raw units; the 589 detailed items sum exactly to the root. Rounded weights per 10000 are preserved but are not used for exact additivity. Tier 1 consists of 10 major groups. Subsequent tiers expand one tree edge at a time; terminal leaves are carried forward so each tier remains an exhaustive, non-overlapping basket. The tier numbers are derived tree depths, not claims of official uniform classification names. Supplementary overlapping aggregates are retained in the master sheet but excluded from these basket tiers. The official hierarchy itself contains all levels and must not be summed across rows as if it were a single basket.

- `processed/japan_cpi_index.csv`: 680 monthly rows, January 1970–August 2026, and 751 item/aggregate columns. Index base: 2025 = 100.
- `processed/japan_cpi_mom_percent.csv`: official percentage changes from the previous month.
- `processed/japan_cpi_yoy_percent.csv`: official percentage changes from the same month one year earlier.
- `metadata/series_catalog.csv`: series codes, English/Japanese names, serial numbers, 2025 expenditure weights, and first/last nonmissing index observations.
- `metadata/table_catalog.csv`: descriptions and coverage of all 22 downloaded tables.
- `manifest.json`: source URLs, retrieval timestamps, SHA-256 hashes and coverage.
- `validation.json`: checks on the main monthly panels.
- `raw/`: all 22 original CSVs and the two catalog HTML pages.

The remaining processed files retain their e-Stat file IDs. The 14 monthly tables cover detailed items, subgroups, goods/services groups, the long historical index excluding imputed rent, and the published seasonally adjusted aggregates. The eight annual tables cover index levels and annual inflation rates. The monthly series excluding imputed rent starts in August 1946; detailed component histories start no earlier than January 1970. Annual tables extend through 2025.

## Interpretation and coverage

This is the entire national long-run table collection under the **2025-base classification**, including all columns supplied by the publisher. It is not an archive of every discontinued item or every historical release vintage under previous base years. Earlier observations are the publisher's linked history, not our own splicing of differently based series.

There are 751 published columns in the detailed table, including aggregate and overlapping special-group indices; they are not 751 mutually exclusive expenditure items. Do not sum their weights or feed all aggregates and their constituent items into a model without selecting an appropriate level of detail.

362 series have a nonmissing index in every month from January 1970 through August 2026. There are 745 nonmissing series in the latest month. New items, discontinued coverage and seasonal availability can create gaps. Missing values remain blank, and source markers remain available in raw files. Nothing was imputed or forward-filled. Coverage dates are specific to each table and measure; early rows in percentage-change files can be entirely missing.

The main detailed panels are **not seasonally adjusted**. The official seasonally adjusted tables contain only five aggregate series from 2010. Factor analysis of monthly item inflation requires a separate, considered approach to seasonality.

Weights in these files are the current 2025-base weights, not time-varying historical basket weights. They should not be applied to all historical dates as if they were contemporaneous weights.

The rate files contain **published inflation rates**, not rates recomputed from the rounded index levels. Small discrepancies from recomputed percentage changes are expected. The 2025 average of the rounded headline index is 100.0083, consistent with the 2025 = 100 base.

## Download method and refresh

The successful download used e-Stat's official unauthenticated CSV file-download endpoints. It did **not** use the authenticated statistical REST API: no application ID was configured in the current environment.

Install the packages in `requirements.txt`, then run `python download.py` from this directory to refresh all files. `python download.py --cached` reprocesses existing CSVs and downloads only files that are missing. The script validates unique codes, unique periods, monthly continuity and expected catalog counts.

An optional `python download.py --api` mode is prepared for national table `0004052037`, using `ESTAT_APP_ID` or `ESTAT_API_KEY` from the local environment. It saves paginated raw JSON separately. This authenticated path has **not been run or verified without an application ID** and does not replace the CSV processing path. Do not put credentials in source code. The API may include additional dimensions beyond the CSV collection.

## Sources

- [Statistics Bureau CPI](https://www.stat.go.jp/english/data/cpi/)
- [2025-base e-Stat catalog](https://www.e-stat.go.jp/en/stat-search/files?tstat=000001243876)
- [Notes for users](https://www.stat.go.jp/english/data/cpi/riyou.html)
- [API access requirements](https://www.e-stat.go.jp/api/en/api-dev/how_to_use)

Attribution: Statistics Bureau, Ministry of Internal Affairs and Communications, Consumer Price Index.
