# Current model charts

Open the [interactive research-results dashboard](../results_dashboard.html) to review the macroeconomic models and selected master’s dissertation results. The dashboard is organised first by modelling framework—MCT, SMOG state space and inflation VAR—with country tabs inside each model family. `results_dashboard_config.py` contains the section order, descriptions, data paths and chart-series definitions; `build_results_dashboard.py` creates the page at the top level of `michaelwjones`.

The [Current Model Charts](Current%20Model%20Charts) folder is the central static gallery for the latest saved outputs. From the repository root, run `py -3.14 Charts/build_model_summary.py` to refresh the static gallery and `py -3.14 Charts/build_results_dashboard.py` to rebuild the dashboard. The dashboard builder refits the existing VAR specifications to export scenario coefficients and checks that their baseline forecasts match the saved results; it does not overwrite those results. Run `py -3.14 macro-work/run_all_var_models.py` to update the AU, JP and KR forecasts first and then refresh both presentations automatically.

## Driver scenarios

Under **Inflation VAR**, select a country, choose a driver on the right, and draw across the shaded future area. Australia and Korea offer oil, unemployment and inflation expectations; Japan offers oil and unemployment because its existing VAR has no expectations variable. These are unemployment rates, not vacancy-to-unemployment ratios. Switch drivers to combine multiple drawn paths; existing edits remain active. Every measure for the country updates immediately, including Japan's national/Tokyo charts and Korea's CPI/PPI charts. Arrow keys adjust a focused point by $1 for oil or 0.1 percentage points for the other drivers. Numeric controls provide an exact-value alternative. **Reset this driver** removes only its assumptions; **Reset country forecasts** clears all drivers. Reloading clears edits.

Australia uses quarterly observations; Japan and Korea use monthly observations. Oil stays in USD-per-barrel levels; unemployment and expectations stay in percentage levels. The editor displays the first measure's paths. Each active driver is imposed at the drawn values on edited dates and its own model baseline on undrawn dates. Drivers with no edits remain endogenous and respond to the combined scenario; their displayed scenario paths reflect those responses. The same dated assumptions apply to every measure for the country. Coefficients remain fixed, with effects entering through lags. These are mechanical scenarios, not structurally identified causal shocks or probability forecasts.

`inflation_scenarios.py` exports the fitted coefficients and initial state into the HTML; `inflation_scenarios.js` runs the editor entirely in the browser. No backend is needed. Run `python Charts/test_inflation_scenarios.py` from the repository root (Python model dependencies and Node.js required) to check all 13 measures against statsmodels, including baseline identity, separate and combined driver paths, lag timing and year-on-year reconstruction.

The Tokyo export now ends observed CPI at the common VAR sample cutoff before chaining forecasts. This fixes the previously duplicated July 2026 row caused by Tokyo CPI being available ahead of the other drivers; estimation and coefficients are unchanged.

## Australia

![AU inflation forecast](Current%20Model%20Charts/AU%20-%20Inflation%20Forecast.png)

![AU MCT core smoothed state](Current%20Model%20Charts/AU%20-%20MCT%20Core%20Smoothed.png)

![AU MCT core filtered state](Current%20Model%20Charts/AU%20-%20MCT%20Core%20Filtered.png)

![AU MCT sector trends](Current%20Model%20Charts/AU%20-%20MCT%20Sector%20Trends.png)

![AU MCT headline smoothed state](Current%20Model%20Charts/AU%20-%20MCT%20Headline%20Smoothed.png)

![AU MCT headline filtered state](Current%20Model%20Charts/AU%20-%20MCT%20Headline%20Filtered.png)

![AU MCT headline sector trends](Current%20Model%20Charts/AU%20-%20MCT%20Headline%20Sector%20Trends.png)

![AU SMOG output gap](Current%20Model%20Charts/AU%20-%20SMOG%20Output%20Gap.png)

![AU SMOG unemployment and NAIRU](Current%20Model%20Charts/AU%20-%20SMOG%20Unemployment%20and%20NAIRU.png)

![AU SMOG unemployment gap](Current%20Model%20Charts/AU%20-%20SMOG%20Unemployment%20Gap.png)

## Japan

![JP national inflation forecast](Current%20Model%20Charts/JP%20-%20National%20Inflation%20Forecast.png)

![JP Tokyo inflation forecast](Current%20Model%20Charts/JP%20-%20Tokyo%20Inflation%20Forecast.png)

![JP MCT core inflation](Current%20Model%20Charts/JP%20-%20MCT%20Core%20Inflation.png)

![JP MCT core filtered state](Current%20Model%20Charts/JP%20-%20MCT%20Core%20Filtered.png)

![JP SMOG output gap](Current%20Model%20Charts/JP%20-%20SMOG%20Output%20Gap.png)

![JP SMOG unemployment and NAIRU](Current%20Model%20Charts/JP%20-%20SMOG%20Unemployment%20and%20NAIRU.png)

![JP SMOG unemployment gap](Current%20Model%20Charts/JP%20-%20SMOG%20Unemployment%20Gap.png)

## Korea

![KR CPI inflation forecast](Current%20Model%20Charts/KR%20-%20CPI%20Inflation%20Forecast.png)

![KR PPI inflation forecast](Current%20Model%20Charts/KR%20-%20PPI%20Inflation%20Forecast.png)

![KR MCT core inflation proxy](Current%20Model%20Charts/KR%20-%20MCT%20Core%20Inflation.png)

![KR MCT core filtered state](Current%20Model%20Charts/KR%20-%20MCT%20Core%20Filtered.png)

The Korean SMOG gallery contains separate smoothed and filtered charts for the output gap, unemployment and NAIRU, and the unemployment gap.

![KR SMOG smoothed output gap](Current%20Model%20Charts/KR%20-%20SMOG%20Output%20Gap%20-%20Smoothed.png)

![KR SMOG filtered output gap](Current%20Model%20Charts/KR%20-%20SMOG%20Output%20Gap%20-%20Filtered.png)

![KR SMOG smoothed unemployment and NAIRU](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20and%20NAIRU%20-%20Smoothed.png)

![KR SMOG filtered unemployment and NAIRU](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20and%20NAIRU%20-%20Filtered.png)

![KR SMOG smoothed unemployment gap](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20Gap%20-%20Smoothed.png)

![KR SMOG filtered unemployment gap](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20Gap%20-%20Filtered.png)

## United States

![USA MCT core inflation](Current%20Model%20Charts/USA%20-%20MCT%20Core%20Inflation.png)

Every MCT implementation now saves both the original full-sample smoothed estimate and a one-sided filtered-state estimate with central 66.7% posterior intervals. Each country implementation is self-contained. Australia has separate `mct_model_core` and `mct_model_headline` folders; neither imports or links to the US implementation or to the other Australian model.
