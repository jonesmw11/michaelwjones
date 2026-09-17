# KR SMOG Model

This standalone South Korean small multivariate output gap model estimates the output gap, potential output, and the NAIRU. It follows the layout and chart style of the AU SMOG folder. Korea's fitted specification has **four** observed signals: GDP, unemployment, core inflation, and nominal unit labour cost growth.

The three scripts in [code](code) import only Python packages and each other. They do not call EViews, load a workfile, or read files outside this folder.

1. [kr_smog_model_generation.py](code/kr_smog_model_generation.py) builds the 2000Q1–2022Q4 historical model from the `Generation` tab, estimates all 18 coefficients by maximum likelihood in Python, and saves the fitted coefficients and initial state to `kr_smog_fitted_parameters.json`.
2. [kr_smog_model_update.py](code/kr_smog_model_update.py) keeps the historical sample fixed and appends new quarters from the `Update` tab. It saves smoothed and filtered states and refreshes the figures.
3. [kr_smog_figure_generation.py](code/kr_smog_figure_generation.py) redraws the six charts from saved states without rerunning the model.

## Run

From this folder:

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 code/kr_smog_model_generation.py
py -3.14 code/kr_smog_model_update.py
# Optional: redraw charts without updating the states
py -3.14 code/kr_smog_figure_generation.py
```

After adding a complete quarter to the `Update` tab in `code/KR SMOG Model Inputs.xlsx`, run the update script. `py -3.14 code/kr_smog_model_update.py --check-only` calculates without replacing results or charts. The generation script is for deliberate changes to the historical model or fitted coefficients.

## Files

- [code/KR SMOG Model Inputs.xlsx](code/KR%20SMOG%20Model%20Inputs.xlsx) has two tabs. `Generation` contains the historical transformed signals and HP initial values used for the 2000Q1–2022Q4 fit. The eight rows after 2022Q4 are red and excluded from generation and the update history. `Update` contains the raw quarterly inputs for subsequent periods and observed unemployment for the charts.
- [kr_smog_fitted_parameters.json](kr_smog_fitted_parameters.json) stores the converged Python fit, its log likelihood, and the initial state for updates.
- [output/kr_smog_fit_history.csv](output/kr_smog_fit_history.csv) records the starting point (iteration 0) and every accepted optimizer iteration, with all 18 coefficients, the full-sample log likelihood, and its change from the preceding iteration.
- [output/kr_smog_fit_likelihood_by_quarter.csv](output/kr_smog_fit_likelihood_by_quarter.csv) records each quarter's contribution to the likelihood at each iteration. Both history files are replaced on every generation run; line-search trial evaluations are not included.
- [output/smog_kr_smoothed_states.csv](output/smog_kr_smoothed_states.csv) is the historical smoothed result.
- [results/smog_kr_python.csv](results/smog_kr_python.csv) and [results/smog_kr_filtered_states.csv](results/smog_kr_filtered_states.csv) contain the extended states through the latest complete quarter.
- [results/figures](results/figures/README.md) contains the six charts and their descriptions.
- [SMOG Model - by RBA.pdf](SMOG%20Model%20-%20by%20RBA.pdf) is bundled background documentation.

The generation data is the saved historical data vintage. The update tab contains later observations, so a refreshed historical source series does not silently change the original fit. The KR model includes a separate wage signal and scales the gap shock variance by 1/100; these are KR-specific parts of the specification.

## Verification

The Python fit converged after 129 iterations on 92 historical quarters, with log likelihood **12.3840**. The fixed-parameter update produced 105 quarters through **2026Q1**. All six charts were generated from the local result CSVs and `Update` tab.

[Back to macro work](../README.md)
