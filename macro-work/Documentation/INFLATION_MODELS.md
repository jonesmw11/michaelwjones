# Inflation models

The [USA inflation project](USA%20Inflation%20Model/README.md) contains national CPI and PCE histories and the Bayesian MCT reconstruction.

Python vector autoregression (VAR) forecasts live in [AU](../AU/Inflation%20Model/README.md), [JP](../JP/Inflation%20Model/README.md), and [KR](../KR/Inflation%20Model/README.md). Each country folder contains its model code, input workbook, saved forecast CSVs, charts and analysis.

The input workbooks are selected values from `Macro Work/Data Inputs.xlsx` in the original research folder. Australia includes the `AU` and `AU-M` sheets; Japan includes `JN`; Korea includes `KR`. Each sheet contains only its model's price measures, drivers, and date columns. The values are a snapshot through 2026Q2 for Australia and June 2026 for Japan and Korea. Later dated but empty rows in the Japanese source were excluded.

## Reproduce

From the `macro-work` folder, with Python 3.14:

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 run_all_var_models.py
```

`run_all_var_models.py` estimates each country's VARs, replaces the forecast CSVs, and draws all five charts. From the repository root, run `py -3.14 Charts/make_charts.py` to refresh only the charts from saved CSVs. The charts use the same typography, green accent, pale grid, and open frame as the SMOG figures. Solid lines show observed year-ended inflation; dashed lines show the forecast. A dotted rule marks the final observation.

Each price index enters its VAR as a period-on-period percentage change. The other drivers enter as documented in the country files. `statsmodels` selects the lag order by AIC and projects all variables jointly. Forecast changes are chained to the latest observed index and converted to year-ended inflation. The CSVs include historical and forecast index levels and year-ended rates. These are statistical projections conditional on the saved data vintage and the VAR specifications, not judgmental forecast paths.

The source implementation came from the original `Macro Work/Inflation` folder. Its older EViews files are not used here. The shared repository-level `Charts/chartstyle.py` comes from the original `Macro Work/Interest Rates` charts so the portfolio charts are self-contained.

[Back to macro work](../README.md)
