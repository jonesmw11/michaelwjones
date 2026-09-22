# South Korea Multivariate Core Trend

This folder is a self-contained copy of the New York Fed-style MCT implementation adapted to South Korea. It does not import code or results from the US model.

The monthly model uses the twelve national expenditure divisions from KOSIS, January 1985 through August 2026, with official 2022 division weights. Food and non-alcoholic beverages is estimated but receives zero weight in the aggregate. The official CPI excluding food and energy is shown for context.

Important limitation: the stored current KOSIS panel is division-level. Energy remains embedded in the housing and transport divisions, so the estimated aggregate is a core proxy rather than an exact component-level exclusion of food and energy. This is stated in every diagnostic output and in the dashboard.

Each production run saves both the original full-sample smoothed MCT and a one-sided filtered-state MCT. The filtered state for month t conditions only on observations through t, while its time-varying parameters remain posterior draws estimated from the full sample; it is not a vintage-data real-time backtest.

```powershell
python prepare_inputs.py
python run_pipeline.py --draws 3000 --burn 3000 --thin 2 --seed 2022
```

Short runs are execution tests or exploratory estimates only. A single 3,000-draw chain does not establish convergence.
