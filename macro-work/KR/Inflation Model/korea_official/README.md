# Official Korean CPI — file-based import in progress

`../Korea CPI - Official Weights.xlsx` is a **partial delivery**, containing official 2022 basket weights for 12 expenditure divisions and 458 representative items. The published item weights sum to 1,000; dividing by 1,000 makes both exhaustive sets sum to 1 without adjustment. Within-division shares also sum to 1. Index reference year is 2020, distinct from the 2022 weight reference year. These are not historical weight vintages.

`../Korea CPI - Partial History.xlsx` now contains the successfully retrieved January 1965–December 1990 export: 312 months, 397 series with some data, and 44,532 nonmissing observations. It includes separate classification-tier sheets, percentage-change sheets, individual series coverage, source hashes, and the official item and division weights. It is explicitly partial. Missing early observations are retained as blanks. The intermediate tier weights are not yet joined to classification codes.

The earlier claim that the first historical download had not saved was incorrect: it was found in Downloads and copied to `raw/history_1965_1990.csv`. KOSIS successfully generated two further CSV exports on 19 September 2026: `101_DT_1J22001_20260919170649.csv` (1991–2015) and `101_DT_1J22001_20260919171001.csv` (2016–August 2026). These files were not yet accessible on disk at the last check. The remaining obstacle is receiving those browser downloads, not a demonstrated requirement for an API key.

To merge saved English exports, run `python build_history.py "path/to/export.csv"`. Use the national series, all classification levels, monthly periods, CSV, Including code, and time periods on the head. KOSIS limits large downloads to 200,000 cells; use bounded periods. The importer archives each input by content hash, merges by official item code, preserves missing values, and lets newer nonmissing observations replace overlapping older exports. Re-run without arguments to rebuild from the archived files. Import a recent overlapping period for monthly updates; periodically refresh the full history for revisions. Downloading is still a browser step, not an unattended update pipeline.

Run `python build_weights.py` with pandas, openpyxl and XlsxWriter. The official source spreadsheet is retained in `raw/weights_2022.xlsx`. `weight_checks.json` records successful totals and the historical-data blocker. Other raw HTML files are diagnostic responses, not data.

Sources:
- https://www.mods.go.kr/twcp/file/cpi_dl_2022.xlsx
- https://www.mods.go.kr/menu.es?mid=b70101040000
- https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1J22001&language=en
