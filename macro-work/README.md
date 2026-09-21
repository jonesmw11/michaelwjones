# Macro work

Macroeconomic research and coding projects.

[Open the interactive research-results dashboard](../results_dashboard.html) for the latest inflation, MCT, SMOG and master’s dissertation results.

## Countries

- **AU:** [Inflation Model](AU/Inflation%20Model/README.md) · [SMOG Model](AU/SMOG%20Model/README.md)
- **JP:** [Inflation Model](JP/Inflation%20Model/README.md) · [SMOG Model](JP/SMOG%20Model/README.md)
- **KR:** [Inflation Model](KR/Inflation%20Model/README.md) · [SMOG Model](KR/SMOG%20Model/README.md)
- **USA:** [Inflation Model](USA/Inflation%20Model/README.md), including CPI and PCE data and the Bayesian MCT reconstruction

Run `py -3.14 run_all_var_models.py` to rebuild the AU, JP and KR VAR forecasts and their charts. It does not run the SMOG or US MCT models.

[Shared inflation workflow](Documentation/INFLATION_MODELS.md) documents the VAR runner and dependencies. The repository-level [Charts](../Charts/README.md) folder contains the static summary gallery and the code used to build both the static charts and interactive dashboard. General reference material is grouped in [Documentation](Documentation), and inactive shared material is retained in [Archive](Archive).

Create a separate folder for each project, with its code, supporting materials, and a README explaining the question, methods, results, and how to run the analysis. The [project README template](../templates/project-README.md) provides a starting point.

[Back to the portfolio](../README.md)
