# Master's dissertation

Code, input data, and the final PDF for my MSc Statistical Science dissertation.

## Overview

The analysis calibrates option-pricing models to a KOSPI 200 option chain and validates the models against Schoutens' S&P 500 data. The code covers Black-Scholes, Levy models, BNS models, stochastic time changes, moments, and implied volatility.

## Folder guide

- [Final dissertation PDF](Michael%20Jones%20MSc%20Statistical%20Science%20Dissertation%20Final.pdf).
- [dissertation_full.py](code/dissertation_full.py) — complete analysis with repository-local input paths and input validation.
- [KOSPI 200 option data](code/KOSPI%20200%20option%20data.csv).
- [S&P 2002 validation data](code/S%26P%202002%20validation%20data.xlsx) — S&P 500 validation input, read from the `Schoutens Data` worksheet.
- [Model results](results/README.md) — 19 saved KOSPI 200 calibration CSVs, one per model.
- [Selected dissertation figures](figures/README.md) — 14 PNG charts covering the data, Black–Scholes, Lévy models, and the best-fitting model comparison.

## Running the code

Use Python 3.11 or later. From the repository's top-level folder, install the dependencies and check the bundled inputs:

```powershell
python -m pip install -r masters-dissertation/requirements.txt
python masters-dissertation/code/dissertation_full.py --check-inputs
```

Then start the full analysis:

```powershell
python -u masters-dissertation/code/dissertation_full.py
```

On Windows, `py -3.14` can replace `python` when using the Python launcher. Inputs resolve relative to the script itself, so it also works when launched by absolute path from another directory. No files from the original Stats Research directory are required.

Allow approximately 14 hours for a full run, depending on the machine. Results are printed to the terminal; the script does not overwrite the saved result CSVs. To retain the printed output, redirect it to a log:

```powershell
python -u masters-dissertation/code/dissertation_full.py > masters-dissertation/run.log 2>&1
```

## Execution checks

```powershell
python masters-dissertation/tests/smoke_check.py
```

The smoke check loads both datasets, runs the KOSPI implied-volatility and Black-Scholes sections, and exercises all 20 model pricing paths on both datasets, using short calibration calls for the Levy and stochastic time-change models. It skips the expensive full calibration loops and density tables; it does not validate convergence or reproduce the dissertation's final results.

Checked with Python 3.14.6, NumPy 2.5.1, pandas 3.0.5, SciPy 1.18.0, and openpyxl 3.1.5. Some GH trial parameters produce numerical warnings; the fitting objective rejects nonfinite trial prices. The full 14-hour numerical analysis has not been rerun for this portfolio copy.

## Data

Both file inputs used by the script are included in the `code` folder:

- KOSPI 200: `code/KOSPI 200 option data.csv` — 212 option contracts, including strikes, expiries, bid/ask and mid prices, and implied volatilities.
- Schoutens S&P 500: `code/S&P 2002 validation data.xlsx`, worksheet `Schoutens Data` — 75 contracts.

Both datasets are validated before any calibration starts, including required numeric columns, finite values, positive strikes/maturities/prices, and consistent spot prices. No live data connection is needed.

## Findings and limitations

See the final dissertation PDF for results, assumptions, and limitations.

[Back to the portfolio](../README.md)
