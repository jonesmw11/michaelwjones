# Current model charts

Open the [interactive research-results dashboard](../results_dashboard.html) to review the macroeconomic models and selected master’s dissertation results. `results_dashboard_config.py` contains the section order, descriptions, data paths and chart-series definitions; `build_results_dashboard.py` creates the page at the top level of `michaelwjones`.

The [Current Model Charts](Current%20Model%20Charts) folder is the central static gallery for the latest saved outputs. From the repository root, run `py -3.14 Charts/build_model_summary.py` and `py -3.14 Charts/build_results_dashboard.py` to refresh both presentations without rerunning any model. Run `py -3.14 macro-work/run_all_var_models.py` to re-estimate the AU, JP and KR VAR forecasts first and then refresh both automatically.

## Australia

![AU inflation forecast](Current%20Model%20Charts/AU%20-%20Inflation%20Forecast.png)

![AU SMOG output gap](Current%20Model%20Charts/AU%20-%20SMOG%20Output%20Gap.png)

![AU SMOG unemployment and NAIRU](Current%20Model%20Charts/AU%20-%20SMOG%20Unemployment%20and%20NAIRU.png)

![AU SMOG unemployment gap](Current%20Model%20Charts/AU%20-%20SMOG%20Unemployment%20Gap.png)

## Japan

![JP national inflation forecast](Current%20Model%20Charts/JP%20-%20National%20Inflation%20Forecast.png)

![JP Tokyo inflation forecast](Current%20Model%20Charts/JP%20-%20Tokyo%20Inflation%20Forecast.png)

![JP SMOG output gap](Current%20Model%20Charts/JP%20-%20SMOG%20Output%20Gap.png)

![JP SMOG unemployment and NAIRU](Current%20Model%20Charts/JP%20-%20SMOG%20Unemployment%20and%20NAIRU.png)

![JP SMOG unemployment gap](Current%20Model%20Charts/JP%20-%20SMOG%20Unemployment%20Gap.png)

## Korea

![KR CPI inflation forecast](Current%20Model%20Charts/KR%20-%20CPI%20Inflation%20Forecast.png)

![KR PPI inflation forecast](Current%20Model%20Charts/KR%20-%20PPI%20Inflation%20Forecast.png)

The Korean SMOG gallery contains separate smoothed and filtered charts for the output gap, unemployment and NAIRU, and the unemployment gap.

![KR SMOG smoothed output gap](Current%20Model%20Charts/KR%20-%20SMOG%20Output%20Gap%20-%20Smoothed.png)

![KR SMOG filtered output gap](Current%20Model%20Charts/KR%20-%20SMOG%20Output%20Gap%20-%20Filtered.png)

![KR SMOG smoothed unemployment and NAIRU](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20and%20NAIRU%20-%20Smoothed.png)

![KR SMOG filtered unemployment and NAIRU](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20and%20NAIRU%20-%20Filtered.png)

![KR SMOG smoothed unemployment gap](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20Gap%20-%20Smoothed.png)

![KR SMOG filtered unemployment gap](Current%20Model%20Charts/KR%20-%20SMOG%20Unemployment%20Gap%20-%20Filtered.png)

## United States

![USA MCT core inflation](Current%20Model%20Charts/USA%20-%20MCT%20Core%20Inflation.png)

The MCT figure is rebuilt from the completed 3,000-draw reconstruction and uses the same house style as the other macro charts. Its shaded region is the central 66.7% posterior interval.
