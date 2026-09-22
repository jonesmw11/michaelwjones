# Export a completed country MCT run to labelled tables, diagnostics, and charts.

# =============================================================================
# %% Imports and paths
import argparse
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parent


# =============================================================================
# %% Helpers
def scalar_text(value):
    array = np.asarray(value).reshape(-1)
    return str(array[0])


def load_inputs():
    paths = list((ROOT / "data").glob("*_core.mat"))
    if len(paths) != 1:
        raise ValueError("Expected exactly one country input MAT file")
    return loadmat(paths[0], simplify_cells=True)


def date_index(data):
    codes = [str(value) for value in np.atleast_1d(data["period_codes"])]
    if scalar_text(data["frequency"]) == "Q":
        return pd.PeriodIndex(codes, freq="Q").to_timestamp(how="end").normalize()
    return pd.to_datetime(codes)


# =============================================================================
# %% Export result files
def export(path):
    path = Path(path)
    result = loadmat(path, simplify_cells=True)
    data = load_inputs()
    dates = date_index(data)
    labels = [str(value) for value in np.atleast_1d(data["labels"])]
    settings = result["settings"]
    sampling = (int(settings["n_draw"]), int(settings["n_burn"]), int(settings["n_thin"]))
    production = sampling == (3000, 3000, 2)

    frame = pd.DataFrame(result["MCT"], index=dates, columns=["lower_16.67pct", "MCT_median", "upper_83.33pct"])
    frame.index.name = "Date"
    filtered_frame = pd.DataFrame(result["MCT_filtered"], index=dates, columns=["lower_16.67pct", "MCT_median", "upper_83.33pct"])
    filtered_frame.index.name = "Date"
    sector_trends = pd.DataFrame(result["sector_trend"], index=dates, columns=labels)
    contributions = pd.DataFrame(result["sector_contribution"], index=dates, columns=labels)
    weights = pd.DataFrame(data["weights"], index=dates, columns=labels)
    context = pd.DataFrame({
        "headline_yoy": np.asarray(data["headline_yoy"], dtype=float),
        "official_core_yoy": np.asarray(data["official_core_yoy"], dtype=float),
    }, index=dates)

    assert np.isfinite(frame.to_numpy()).all()
    assert (frame.iloc[:, 0] <= frame.iloc[:, 1]).all()
    assert (frame.iloc[:, 1] <= frame.iloc[:, 2]).all()
    assert np.isfinite(filtered_frame.to_numpy()).all()
    assert (filtered_frame.iloc[:, 0] <= filtered_frame.iloc[:, 1]).all()
    assert (filtered_frame.iloc[:, 1] <= filtered_frame.iloc[:, 2]).all()
    np.testing.assert_allclose(weights.sum(axis=1), 1, atol=1e-12)

    labelled_path = path.with_name(path.stem + "_labelled.csv")
    filtered_path = path.with_name(path.stem + "_filtered_labelled.csv")
    trend_path = path.with_name(path.stem + "_sector_trends.csv")
    contribution_path = path.with_name(path.stem + "_sector_contributions.csv")
    weight_path = path.with_name(path.stem + "_weights.csv")
    context_path = path.with_name(path.stem + "_context.csv")
    frame.to_csv(labelled_path)
    filtered_frame.to_csv(filtered_path)
    sector_trends.to_csv(trend_path)
    contributions.to_csv(contribution_path)
    weights.to_csv(weight_path)
    context.to_csv(context_path)
    for source, name in [
        (labelled_path, "latest_labelled.csv"),
        (filtered_path, "latest_filtered_labelled.csv"),
        (trend_path, "latest_sector_trends.csv"),
        (contribution_path, "latest_sector_contributions.csv"),
        (weight_path, "latest_weights.csv"),
        (context_path, "latest_context.csv"),
    ]:
        shutil.copyfile(source, path.parent / name)

    finite_core = context["official_core_yoy"].dropna()
    diagnostics = {
        "country": scalar_text(data["country"]),
        "target": scalar_text(data["target_name"]),
        "status": "Production sampling settings" if production else "Exploratory sampling settings; not a production estimate",
        "draws": sampling[0],
        "burn_in": sampling[1],
        "thinning": sampling[2],
        "elapsed_seconds": float(result["elapsed_seconds"]),
        "first_date": str(dates[0].date()),
        "latest_date": str(dates[-1].date()),
        "latest_mct_median": float(frame.MCT_median.iloc[-1]),
        "latest_filtered_mct_median": float(filtered_frame.MCT_median.iloc[-1]),
        "latest_official_core_yoy": float(finite_core.iloc[-1]) if len(finite_core) else None,
        "limitation": scalar_text(data["limitation"]),
        "convergence": "Not established by a single chain; inspect independent seeds before substantive use.",
    }
    path.with_suffix(".json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    (path.parent / "latest_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(dates, frame.iloc[:, 0], frame.iloc[:, 2], color="#0B6E4F", alpha=0.16, label="Central 66.7% interval")
    ax.plot(dates, frame.MCT_median, color="#0B6E4F", lw=2.2, label="MCT estimate")
    if len(finite_core):
        ax.plot(finite_core.index, finite_core, color="#8A8A8A", lw=1.2, label="Official core, year ended")
    ax.axhline(2, color="#B5651D", lw=1.2, ls=":", label="2% reference")
    ax.set_title(f"{diagnostics['country']}: Multivariate Core Trend")
    ax.set_ylabel("Annualized inflation, percent")
    ax.legend(frameon=False)
    fig.tight_layout()
    chart_path = path.with_suffix(".png")
    fig.savefig(chart_path, dpi=160)
    plt.close(fig)
    shutil.copyfile(chart_path, path.parent / "latest.png")
    chart_destination = ROOT.parents[3] / "Charts/Current Model Charts" / f"{diagnostics['country'].replace('South Korea', 'KR').replace('Australia', 'AU').replace('Japan', 'JP')} - MCT Core Inflation.png"
    chart_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(chart_path, chart_destination)

    # =============================================================================
    # %% Export the one-sided filtered-state comparison chart
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(dates, filtered_frame.iloc[:, 0], filtered_frame.iloc[:, 2], color="#5BAE95", alpha=0.22, label="Filtered central 66.7% interval")
    ax.plot(dates, filtered_frame.MCT_median, color="#0B6E4F", lw=2.2, label="Filtered MCT")
    ax.plot(dates, frame.MCT_median, color="#6B7280", lw=1.3, ls="--", label="Smoothed MCT")
    if len(finite_core):
        ax.plot(finite_core.index, finite_core, color="#9A9A9A", lw=1.1, alpha=0.75, label="Official core, year ended")
    ax.axhline(2, color="#B5651D", lw=1.2, ls=":", label="2% reference")
    ax.set_title(f"{diagnostics['country']}: Filtered vs Smoothed MCT")
    ax.set_ylabel("Annualized inflation, percent")
    ax.legend(frameon=False)
    fig.tight_layout()
    filtered_chart_path = path.with_name(path.stem + "_filtered.png")
    fig.savefig(filtered_chart_path, dpi=160)
    plt.close(fig)
    shutil.copyfile(filtered_chart_path, path.parent / "latest_filtered.png")
    shutil.copyfile(filtered_chart_path, ROOT.parents[3] / "Charts/Current Model Charts/JP - MCT Core Filtered.png")
    print(json.dumps(diagnostics, indent=2))


# =============================================================================
# %% Command-line entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    export(parser.parse_args().result.resolve())
