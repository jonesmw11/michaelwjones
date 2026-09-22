# Australia Multivariate Core Trend — Headline

`mct_model_headline` is a self-contained quarterly MCT implementation for Australian headline CPI. It does not import code or results from the US model or `mct_model_core`.

The longer sample runs from 1972 Q4 through 2026 Q2. Six expenditure groups have continuous official quarterly histories from 1972 Q3: food, alcohol and tobacco, clothing and footwear, housing, furnishings and household services, and transport. A seventh residual sector represents all remaining goods and services. Under fixed 2025 weights, its index is constructed so the seven-sector basket exactly reproduces the official headline CPI index.

The estimator retains time-varying common and sector trends, stochastic volatility, MA(3) quarterly noise, and outlier mixtures. Quarterly changes are annualized. Historical fixed-weight decomposition is an approximation and a single chain does not establish convergence.

Each production run saves both the original full-sample smoothed MCT and a one-sided filtered-state MCT. The filtered state for quarter t conditions only on observations through t, while its time-varying parameters remain posterior draws estimated from the full sample; it is not a vintage-data real-time backtest.

```powershell
python prepare_inputs.py
python run_pipeline.py --draws 3000 --burn 3000 --thin 2 --seed 2022
```
