# USA CPI data

[NY Fed MCT model recreation](mct_model/README.md) contains the official estimator, an original-data replication, and a separately labelled updated BEA-data reconstruction. See its run status and comparison reports before using estimated results.

[Core and underlying inflation histories](USA%20-%20Core%20Inflation%20Measures.xlsx) combine CPI/PCE exclusions with Cleveland, Dallas, Atlanta and New York Fed underlying measures. The shared construction pipeline and combined workbook are archived; this country workbook remains active.

## PCE companion workbook

[USA PCE - Historical Data and Weights.xlsx](USA%20PCE%20-%20Historical%20Data%20and%20Weights.xlsx) adds official BEA PCE price and spending histories, monthly inflation changes, eight classification tiers, and time-varying expenditure shares. See [PCE documentation](pce_official/README.md) for coverage, refresh instructions, and the distinction between expenditure shares and Fisher chain weights. The CPI workbook below remains separate.

[USA CPI - Historical Data and Weights.xlsx](USA%20CPI%20-%20Historical%20Data%20and%20Weights.xlsx) contains **400 national, not seasonally adjusted CPI-U series**, with 225,468 index observations spanning January 1913 to August 2026 across the dataset. Individual series have different start and end dates; discontinued series are retained. This folder contains data preparation, not an estimated US inflation forecast.

The workbook includes:

- **All National CPI Data:** one master sheet of the available monthly histories, including special aggregates and two purchasing-power series.
- **Inflation MoM percent / Inflation YoY percent:** derived percentage changes using the exact preceding month or corresponding month a year earlier. Purchasing-power series are excluded from these inflation sheets.
- **Tier 1 / Tier 2 / Tier 3:** 8 major groups, 70 expenditure classes, and 204 finest components supported by the published weight table. Tier 3 carries forward 13 expenditure classes without a separately weighted breakdown; it does not claim to split all 211 BLS item strata.
- Published weights, the parent-child hierarchy, weight ranks, rounding adjustments and an audit of the data refresh.

Each tier's **reconciled basket shares sum to 1** within numerical tolerance of 1e-12. The official December 2025 CPI-U relative-importance percentages, based on 2024 expenditure weights, are preserved alongside the derived shares. Published tier totals are 100.000%, 99.999% and 100.001%. Reconciliation assigns each child its parent's reconciled share multiplied by its proportion of published sibling weights. Child shares therefore sum to their parent as well as each full tier summing to 1.

The 22 explicitly unsampled categories remain in the weight hierarchy, with blank price histories. Removing them and renormalising only observed items would change the basket. The master contains overlapping aggregates, so its rows should not be summed. These weights are a single vintage, not historical time-varying weights, and they do not reproduce the official CPI aggregation formula.

## Sources and historical consistency

The series originate from the [Bureau of Labor Statistics](https://www.bls.gov/cpi/data.htm). Because direct bulk downloads were denied, long histories were obtained from the public [DBnomics BLS mirror](https://db.nomics.world/BLS/cu). All available 2017–2026 observations were then refreshed directly through the [BLS public API](https://www.bls.gov/developers/). The overlap contained 37,398 observations; all disagreements were confined to seven rebased series. Those seven series were subsequently refreshed from BLS **back to their first observation**, avoiding a false jump between old and new reference bases. See the [May 2026 rebasing notice](https://www.bls.gov/cpi/notices/2026/rebasing.htm).

Other series retain their native, series-specific index bases. Do not compare component index levels as though they shared a common base. No observations were interpolated or forward-filled; missing October 2025 observations and the corresponding undefined inflation calculations remain blank.

Weights come from the [official December 2025 relative-importance table](https://www.bls.gov/cpi/tables/relative-importance/2025.htm). The structural tiers follow the [BLS item aggregation definitions](https://www.bls.gov/cpi/additional-resources/cpi-item-aggregation.htm): major groups, expenditure classes and their published components. Published CPI-W weights are retained for reference only; CPI-W histories, PCE, chained CPI, regional CPI and seasonally adjusted series are outside this workbook's scope.

## Reproduce and validate

From `usa_official`:

```powershell
python -m pip install -r requirements.txt
python download_history.py
python prepare_data.py
python build_workbook.py
python validate_workbook.py
```

Raw catalog, historical API responses, BLS responses and official weight-table extracts are retained. Downloads use the cached responses when present, making the delivered vintage reproducible. The scripts are pinned to the delivered 2026 data window; running them is not an automatic update to a future release. `manifest.json` contains raw-file hashes, and `validation.json` records the checks. The saved workbook was read back and every index observation and 436,127 derived inflation values were checked, together with tier history matches, all tier sums and the rebased histories.
