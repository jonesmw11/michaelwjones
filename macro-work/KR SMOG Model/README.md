# KR SMOG Model

This standalone South Korean small multivariate output gap model estimates the output gap, potential output, and the NAIRU. It follows the layout and chart style of the AU SMOG folder. Korea's fitted specification has **four** observed signals: GDP, unemployment, core inflation, and nominal unit labour cost growth.

The three scripts in [code](code) import only Python packages and each other. They do not call EViews, load a workfile, or read files outside this folder.

1. [kr_smog_model_generation.py](code/kr_smog_model_generation.py) builds the 2000Q1–2022Q4 historical model from the `Generation` tab, smooths with the bundled fitted coefficients, and saves the coefficients and initial state to `kr_smog_fitted_parameters.json`.
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

After adding a complete quarter to the `Update` tab, run the update script. `py -3.14 code/kr_smog_model_update.py --check-only` calculates without replacing results or charts. The generation script is for deliberate changes to the historical model or fitted coefficients.

## Files

- [results/KR SMOG Model Inputs.xlsx](results/KR%20SMOG%20Model%20Inputs.xlsx) has two tabs. `Generation` contains the historical transformed signals and HP initial values used for the 2000Q1–2022Q4 fit. The eight rows after 2022Q4 are red and excluded from generation and the update history. `Update` contains the raw quarterly inputs for subsequent periods and observed unemployment for the charts.
- [output/kr_ss1_output.csv](output/kr_ss1_output.csv) is the bundled fitted coefficient table. It is data read by Python; EViews software is not required.
- [output/smog_kr_smoothed_states.csv](output/smog_kr_smoothed_states.csv) is the historical smoothed result.
- [results/smog_kr_python.csv](results/smog_kr_python.csv) and [results/smog_kr_filtered_states.csv](results/smog_kr_filtered_states.csv) contain the extended states through the latest complete quarter.
- [results/figures](results/figures/README.md) contains the six charts and their descriptions.
- [SMOG Model - by RBA.pdf](SMOG%20Model%20-%20by%20RBA.pdf) is bundled background documentation.

The generation data is the saved historical data vintage. The update tab contains later observations, so a refreshed historical source series does not silently change the original fit. The KR model includes a separate wage signal and scales the gap shock variance by 1/100; these are KR-specific parts of the specification.

## Verification

The historical calculation has 92 quarters and reproduces the saved fitted log likelihood **12.3840**. The fixed-parameter update produced 105 quarters through **2026Q1**. All six charts were generated from the local result CSVs and `Update` tab.

[Back to macro work](../README.md)
