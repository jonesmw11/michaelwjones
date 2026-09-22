# Japan Multivariate Core Trend

This folder is a self-contained copy of the New York Fed-style MCT implementation adapted to Japan. It does not import code or results from the US model.

The monthly model estimates eleven disjoint national CPI sectors from January 1970 through August 2026. Fresh food is estimated as a sector but receives zero weight in the final aggregate. The remaining ten sectors use normalized 2025 Statistics Bureau weights, so the target is Japanese CPI excluding fresh food. The official ex-fresh-food twelve-month rate is shown only as context.

The latent model retains time-varying common and sector trends, time-varying loadings, stochastic volatility, MA(3) transitory noise, and outlier mixtures. Monthly price changes are annualized. Historical estimates use fixed current weights and can revise when the sample is extended.

Each production run saves both the original full-sample smoothed MCT and a one-sided filtered-state MCT. The filtered state for month t conditions only on observations through t, while its time-varying parameters remain posterior draws estimated from the full sample; it is not a vintage-data real-time backtest.

```powershell
python prepare_inputs.py
python run_pipeline.py --draws 3000 --burn 3000 --thin 2 --seed 2022
```

Short runs are execution tests or exploratory estimates only. A single 3,000-draw chain does not establish convergence.
