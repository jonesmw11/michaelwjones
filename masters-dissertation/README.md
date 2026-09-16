# Master's dissertation

Code, input data, and the final PDF for my MSc Statistical Science dissertation.

## Overview

The analysis calibrates option-pricing models to a KOSPI 200 option chain and validates the models against Schoutens' S&P 500 data. The code covers Black-Scholes, Levy models, BNS models, stochastic time changes, moments, and implied volatility.

## Folder guide

- [Final dissertation PDF](Michael%20Jones%20MSc%20Statistical%20Science%20Dissertation%20Final.pdf).
- [dissertation_full.py](code/dissertation_full.py) — complete analysis, copied unchanged from the research folder.
- [KOSPI 200 input CSV](code/k200_implied_vol_by_maturity/k200_iv_per_contract.csv).
- [Data.xlsx](code/Data.xlsx) — S&P 500 validation input, read from the `Schoutens Data` worksheet.
- `notebooks/` and `results/` — reserved for future additions.

The `.gitkeep` files keep these folders visible in GitHub until project files are added. They can be removed once the folders contain your work.

## Running the code

Run from the `code` folder so the original relative data paths resolve:

```powershell
cd code
python -m pip install "numpy>=2" pandas scipy openpyxl
python dissertation_full.py
```

The script notes that a complete run takes several hours. The copied files have been checked against the originals; the full numerical analysis has not been rerun for this portfolio copy.

## Data

Both file inputs used by the script are included, with their original filenames and relative locations. The validation input is an Excel workbook rather than a CSV.

## Findings and limitations

See the final dissertation PDF for results, assumptions, and limitations.

[Back to the portfolio](../README.md)
