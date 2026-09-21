# US PCE inflation data

`../USA PCE - Historical Data and Weights.xlsx` contains official BEA data downloaded directly from its public underlying-detail Excel release. No API key or third-party mirror is used. The initial delivery covers January 1959–July 2026, published August 26, 2026. Individual series have different coverage.

## Contents

- All 402 rows of monthly PCE price indexes (Table 2.4.4U), including headline, core, detailed categories and market-based aggregates.
- Corresponding current-dollar spending (Table 2.4.5U), monthly percentage changes and year-over-year inflation.
- Eight exhaustive classification tiers, with price sheets and monthly weight sheets; shorter branches carry forward terminal items.
- Latest weights and ranks, series codes and individual coverage, published spending shares, and numerical hierarchy/weight checks.
- Official annual and quarterly price and spending histories.

Prices are seasonally adjusted, 2017=100. Monthly and quarterly spending is in millions of current dollars at seasonally adjusted annual rates. Monthly growth rates in this workbook are not annualised. Missing values are not filled. Annual and quarterly histories retain the source's period labels.

## Weights and hierarchy

BEA does not publish a fixed PCE basket comparable to CPI weights. Current-dollar expenditure shares approximate relative importance; the official PCE price index uses a Fisher chain formula. The workbook's weights are analytical expenditure shares, **not exact Fisher weights or official inflation contributions**. See [BEA's explanation](https://www.bea.gov/help/faq/1006).

The main basket consists of table lines 1–368. Later rows are overlapping aggregates and are excluded from tier totals. Line numbers, rather than series codes alone, join the price and spending tables, whose labels are verified to match. Published indentation defines the hierarchy. Line 156 is retained unsplit in the deepest tier because lines 157–159 are alternative historical housing breakdowns that are never simultaneously complete.

Published dollar totals are rounded. Reconciled shares allocate each parent's share by its children's signed spending proportions. Every fully observed tier sums to 1 within 1e-12; published figures and unreconciled shares remain available. Historical weights are left incomplete where a complete split is unavailable. No allocation is made by redistributing only across observed children.

Deep tiers include accounting deductions such as receipts from nonprofit sales and spending by nonresidents. `Less:` signs propagate through descendants; negative net expenditure is also retained. Consequently, deep tiers contain **negative shares**, despite summing to 1. They should not be interpreted as positive-only consumption baskets. Every complete parent-child dollar identity is checked against the tolerance implied by rounding to whole millions. Line 156 has no simultaneous complete split, which the audit exposes.

## Rebuild and update

```powershell
python -m pip install -r requirements.txt
python build_pce.py
python validate_pce.py
```

To retrieve a new release, use `python build_pce.py --refresh`, then validate again. This fetches one complete official Excel file (about 12 MB), incorporating historical revisions and new periods. An earlier raw vintage is archived by content hash. It does not poll for releases or require an API key. The parser deliberately stops if the number of table rows changes, so hierarchy changes receive review.

`manifest.json` records the source, raw hash, publication notes and coverage. `validation.json` records workbook read-back checks. CSV copies of monthly prices, spending and metadata are provided for modelling. No forecasting or factor model has been estimated.

Source: [BEA underlying-detail Section 2 workbook](https://apps.bea.gov/national/Release/XLS/Underlying/Section2All_xls.xlsx).
