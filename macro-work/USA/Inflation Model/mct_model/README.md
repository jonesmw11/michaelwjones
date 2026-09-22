# New York Fed Multivariate Core Trend recreation

[Archived guide to understanding and fitting MCT](Archive/Documentation/explanation/Fitting_the_NY_Fed_MCT.pdf) builds from regression and factor models to the actual Bayesian fitting procedure. [Editable archived LaTeX source](Archive/Documentation/explanation/Fitting_the_NY_Fed_MCT.tex).

[Archived research papers and model descriptions](Archive/Documentation/references/README.md): three original PDFs and three official web descriptions, with public links and download provenance.

The default estimator now runs entirely in Python, using **statsmodels** for Gaussian state simulation smoothing and Kalman filtering, **NumPy/SciPy** for the Bayesian updates and linear algebra, and **pandas/XlsxWriter/Matplotlib** for data and reporting. `mct_python.py` translates the published NY Fed monthly model configuration; it is not the simpler off-the-shelf `DynamicFactor` model. It retains time-varying loadings, common and sector trends, stochastic volatility, MA(3) noise and outlier mixtures. The model-specific Gibbs schedule and matrix assembly are custom code; the general numerical algorithms use packages.

The active output in `results/python` is the completed current-data reconstruction using 3,000 burn-in iterations, 3,000 retained draws and thinning of 2. Its MAT, labelled CSV, Excel workbook, chart, JSON report and status JSON are the final result set. New full runs also save filtered estimates to a `_filtered_labelled.csv` file and a `Filtered MCT` workbook sheet, then export a separate `_filtered.png` chart that overlays the smoothed median for comparison. Short smoke-test outputs and run logs are retained separately under `Archive/Python_Results/current_reconstruction_smoke_tests/`. A completed run is not by itself proof of MCMC convergence or a successful numerical replication. The earlier Octave production job was stopped when the Python implementation was requested. Its files are retained as reference material.

## Sources and reproducibility

- [NY Fed model description](https://www.newyorkfed.org/research/policy/mct)
- [Official MATLAB code and data snapshot](https://github.com/MCT-Inflation-NYFed/MCT-PCE), pinned to commit `7e68e46e2ff4ad55b712f2c6c49f08f9c48e1ea1`.
- Active `upstream/` retains the official input data, reference output and BSD license required for input preparation and attribution. Unused upstream MATLAB functions and tables are archived under `Archive/Octave/upstream/`.
- The optional generated Octave runtime and its patch manifest are archived under `Archive/Octave/runtime/`.
- The original driver uses MATLAB. Its source is retained as an independent reference. The same seed does not guarantee the same draws across Python, MATLAB and Octave.
- Python's package state-space smoother is documented [here](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.simulation_smoother.SimulationSmoother.html). NumPy's generator supplies normal, multinomial, gamma and beta draws; SciPy supplies symmetric matrix inversion, block matrices and stable mixture probabilities.
- This port implements the configuration selected by the published PCE driver: all series monthly, three MA lags, and no cross-dependent sectors. Optional time aggregation and cross-sector dependence branches elsewhere in the upstream library are not implemented.

## Model mathematics

For sector i and month t, the measurement equation is

`inflation_it = alphaTrend_it * commonTrend_t + sectorTrend_it + alphaNoise_it * commonNoise_t + sectorNoise_it`.

The persistent part is `trend_it = alphaTrend_it * commonTrend_t + sectorTrend_it`. The common and sector trends follow random walks. The loadings also evolve over time; shock variances have stochastic volatility. The sector transitory component is an MA(3) process, and scale mixtures allow unusually large transitory shocks. The precise priors and initial conditions are those in the upstream implementation.

This is both a dynamic factor model and a state-space model. “Factor” describes the common latent influences shared across sectors. “State space” describes the observation equations and transition equations used to estimate those hidden influences. Conditional on each draw of the loadings, volatilities and other parameters, the Kalman filter and simulation smoother draw the latent states. Bayesian sampling then updates those parameters and repeats.

The aggregate for each posterior draw is

`MCT_t = sum_i coreWeight_it * trend_it`.

The original reported estimate is the posterior median of that aggregate, with the 1/6 and 5/6 quantiles as the central 66.7% interval. Sector contribution medians need not add exactly to the aggregate median: medians are not additive. This is a smoothed estimate of underlying inflation, not automatically an out-of-sample forecast; historical estimates can change with new data.

The separately saved filtered estimate runs the one-sided Kalman filter for each retained posterior parameter draw. The state for month t uses observations only through month t, while the time-varying loadings, volatilities and other parameters are still full-sample posterior draws. It is therefore a filtered-state comparison with the smoother, not a vintage-data real-time backtest.

## Inputs and weights

The model estimates all 17 published sectors but excludes food purchased for off-premises consumption, gasoline/other energy goods, and electricity/gas utilities from the final core aggregate. Restaurant food remains included, following the supplied NY Fed core weights. The remaining 14 weights are normalized current-dollar expenditures and sum to one every month. Monthly sector inflation is annualized as `100 * ((P_t/P_(t-1))^12 - 1)`, matching the source exactly.

`prepare_inputs.py` builds and validates two inputs:

- `replication_202310`: exact upstream numerical inputs, January 1960–October 2023. Transformations are checked against the supplied source data. Compare its estimates to `data/reference_202310.csv` from the same NY Fed vintage.
- `current_reconstruction`: January 1960–July 2026 using the downloaded BEA data in `../pce_official`. This is a reconstruction, not an exact current NY Fed replication. The upstream repository does not supply its housing/utilities preparation script. We combine housing and water/sanitation using a bilateral Fisher chain, with electricity/gas as a separate published index. `data/sector_mapping.csv` records every mapping. Data revisions also prevent a clean comparison with the October 2023 reference.

`input_checks.json` records dates and validation. Do not interpret the two vintages' differences solely as estimation error. No missing data are fabricated or forward-filled in these prepared samples.

## Running and updating

Install the Python requirements. Estimation does not require MATLAB or Octave:

```powershell
python -m pip install -r requirements.txt
python prepare_inputs.py
python run_pipeline.py --vintage both
```

For a short execution test only:

```powershell
python run_python.py --vintage both --draws 10 --burn 20 --thin 2
```

Use `--vintage current_reconstruction` to rerun only the updated data. Refresh the sibling official PCE dataset and run `prepare_inputs.py` before fitting a new vintage. This implementation refits the complete sample; it does not claim an incremental monthly update. Single-thread BLAS is selected before importing numerical libraries to avoid overhead on small matrices. Full-history short-run benchmarks suggest a few hours for each full sampling run; this is only an extrapolation. The computer must remain awake. A failed or interrupted run must restart estimation; partial draws are not checkpointed. Each completed run automatically exports MAT, CSV, Excel, PNG and JSON files under `results/python`.

The original Octave runner and runtime-preparation scripts are preserved under `Archive/Octave/` for reference only. They are not Python estimation dependencies and must be restored to their former paths before use.

The official settings are 3,000 burn-in iterations, 3,000 retained draws and thinning of 2, with seed 2022. Upstream includes iteration zero. The active result files use these settings. Five- and ten-draw smoke tests checked execution and output integrity only; they are archived and must not be used as inflation measures.

## Validation and remaining interpretation

The exporter checks finite estimates, ordered posterior intervals and normalized weights. Each workbook contains the local estimates, same-vintage reference comparison where applicable, sector inflation inputs, weights, trends and contribution medians. JSON reports give comparison errors and settings. For substantive use, inspect trace plots and effective sample sizes, and run independent seeds to assess convergence. A single chain and proximity to published results do not establish convergence. The provided comparison metrics report the evidence rather than applying an arbitrary replication pass threshold.

The optional validation driver and its generated Python/Octave fixtures are archived under `Archive/Validation/`. Its recorded checks covered reproducibility, refreshed Gibbs pseudo-observations, state matrices and conditional smoother means. Those checks validated Gaussian calculations, not the entire posterior distribution or MCMC convergence.

The original driver's volatility, outlier-probability and news-decomposition reports are not exported by this compact MCT runner. All underlying estimation code is retained.
