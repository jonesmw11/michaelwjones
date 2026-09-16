# AU SMOG Model

Australian state-space model for estimating the output gap, potential output, and the non-accelerating inflation rate of unemployment (NAIRU). The model combines output, unemployment, and inflation signals with seven latent states.

[Model documentation](SMOG_AU_Model_Documentation.pdf)

## Contents

| File | Purpose |
| --- | --- |
| `au_pipeline.py` | Raw-data preparation, starting values, and fresh maximum-likelihood estimation for AU SMOG |
| `au.py` | Stored Australian model specifications and EViews coefficients; also contains the separate AU Laubach-Williams specification |
| `statespace.py` | Shared state-space model implementation and replication functions |
| `fitting.py` | Re-estimation using the exported estimation data and documented starting coefficients |
| `smog_data.py` | Input transformations, including the Australian data through 2026Q1 |
| `Estimation Data.xlsx` | Combined estimation workbook; the AU pipeline reads `SMOG AU\|Quarterly` |
| `Model Inputs.xlsx` | Combined input workbook; the AU pipeline reads `AU - Q` |
| `output/au_wf_export.xlsx` | AU EViews estimation data and reference states |
| `output/au_ss1_output.csv` | EViews estimation table, including starting values |
| `output/smog_au_smoothed_states.csv` | Saved raw-pipeline output: 1980Q1–2023Q4 |
| `output/smog_au_gap_comparison.csv` | Saved output-gap comparison |
| `results/smog_au_python.csv` | Saved extended results: 1980Q1–2026Q1 |

The original source files were copied from `Macro Work/Interest Rates`, with the PDF copied from `Macro Work`. Their contents were verified against the originals. The combined workbooks and shared Python modules retain other-country/model content where it is part of those original files.

## Running AU SMOG

From this folder, install dependencies:

```powershell
python -m pip install -r requirements.txt
```

To estimate from raw data and explicitly save the output:

```powershell
python -c "import au_pipeline as p; out = p.main(); p.save_results(out)"
```

This runs the full BFGS / Nelder-Mead / BFGS sequence and writes the smoothed-state CSV and, when matplotlib is installed, an output-gap chart into `output/`. It overwrites the corresponding saved output files.

To replicate AU SMOG at the stored EViews coefficients:

```powershell
python -c "import au, statespace; statespace.run_smog('AU', au.SMOG_SPEC)"
```

This writes `results/smog_au_python.csv` using the bundled workfile export. It does not update the input data to the latest quarter and can overwrite the longer saved series. Running `au.py` directly also invokes the separate LW model, whose inputs are outside this AU SMOG package; use the targeted command above.

## Initial examination

- The raw-data estimation window contains 176 quarters, from 1980Q1 to 2023Q4. Data loading, transformations, starting-value estimation, and initial likelihood evaluation passed.
- Kalman smoothing at stored coefficients passed. The reproduced likelihood was **517.659443**, against the stored EViews value **517.6595**, within the code's tolerance of 0.0005.
- The input builder can load Australian observations through 2026Q1. The saved extended results contain 185 quarters.
- `au_pipeline.main()` returns the result but does not call `save_results()` itself; the command above makes that save step explicit.
- The source handles a documented unemployment-series problem in `Estimation Data.xlsx` by taking unemployment from `Model Inputs.xlsx`.
- Script execution and interactive cells resolve the copied workbooks inside this repository. Open the repository or its AU SMOG folder before running the code as cells.
- A fresh full maximum-likelihood fit and regeneration of the extended results have not been run for this copy.

[Back to macro work](../README.md)
