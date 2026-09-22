# Australia Multivariate Core Trend — Core

`mct_model_core` is a self-contained copy of the New York Fed-style MCT implementation adapted to Australian core inflation. It does not import code or results from the US model or the separate headline model.

The model is quarterly because the official monthly component panel begins only in April 2024. It uses the longer ABS quarterly national CPI history through June 2026. Food and energy are estimated but receive zero weight in the aggregate. Electricity, gas and other household fuels, and automotive fuel are split from housing and transport with a fixed-weight geometric decomposition. The other current ABS groups are retained, and quarterly changes are annualized.

The loading and volatility priors are rescaled from twelve monthly periods to four quarterly periods per year. The model still uses MA(3) transitory noise, now interpreted as three quarters. Fixed 2025 weights and the historical decomposition are approximations, not an official ABS historical core series.

Each production run saves both the original full-sample smoothed MCT and a one-sided filtered-state MCT. The filtered state for quarter t conditions only on observations through t, while its time-varying parameters remain posterior draws estimated from the full sample; it is not a vintage-data real-time backtest.

```powershell
python prepare_inputs.py
python run_pipeline.py --draws 3000 --burn 3000 --thin 2 --seed 2022
```

Short runs are execution tests or exploratory estimates only. A single 3,000-draw chain does not establish convergence.
