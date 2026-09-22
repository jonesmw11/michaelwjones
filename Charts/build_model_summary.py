# Build one central gallery from the latest saved model charts.

# %% Imports and locations
# Use the saved model outputs; this script does not rerun any estimation.
from pathlib import Path
from shutil import copy2

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import chartstyle as style


ROOT = Path(__file__).resolve().parent.parent / "macro-work"
OUTPUT = Path(__file__).resolve().parent / "Current Model Charts"


# %% Existing house-style charts
# Give every chart a readable country, model and measure name in the gallery.
CHARTS = {
    ROOT / "AU/Inflation Model/results/figures/au_inflation_forecast.png": "AU - Inflation Forecast.png",
    ROOT / "JP/Inflation Model/results/figures/jp_cpi_inflation_forecast.png": "JP - National Inflation Forecast.png",
    ROOT / "JP/Inflation Model/results/figures/jp_tokyo_inflation_forecast.png": "JP - Tokyo Inflation Forecast.png",
    ROOT / "KR/Inflation Model/results/figures/kr_cpi_inflation_forecast.png": "KR - CPI Inflation Forecast.png",
    ROOT / "KR/Inflation Model/results/figures/kr_ppi_inflation_forecast.png": "KR - PPI Inflation Forecast.png",
    ROOT / "AU/SMOG Model/results/figures/au_smog_output_gap.png": "AU - SMOG Output Gap.png",
    ROOT / "AU/SMOG Model/results/figures/au_smog_unemployment_and_nairu.png": "AU - SMOG Unemployment and NAIRU.png",
    ROOT / "AU/SMOG Model/results/figures/au_smog_unemployment_gap.png": "AU - SMOG Unemployment Gap.png",
    ROOT / "JP/SMOG Model/results/figures/jp_smog_output_gap.png": "JP - SMOG Output Gap.png",
    ROOT / "JP/SMOG Model/results/figures/jp_smog_unemployment_and_nairu.png": "JP - SMOG Unemployment and NAIRU.png",
    ROOT / "JP/SMOG Model/results/figures/jp_smog_unemployment_gap.png": "JP - SMOG Unemployment Gap.png",
    ROOT / "KR/SMOG Model/results/figures/kr_smog_output_gap_smoothed.png": "KR - SMOG Output Gap - Smoothed.png",
    ROOT / "KR/SMOG Model/results/figures/kr_smog_output_gap_filtered.png": "KR - SMOG Output Gap - Filtered.png",
    ROOT / "KR/SMOG Model/results/figures/kr_smog_unemployment_and_nairu_smoothed.png": "KR - SMOG Unemployment and NAIRU - Smoothed.png",
    ROOT / "KR/SMOG Model/results/figures/kr_smog_unemployment_and_nairu_filtered.png": "KR - SMOG Unemployment and NAIRU - Filtered.png",
    ROOT / "KR/SMOG Model/results/figures/kr_smog_unemployment_gap_smoothed.png": "KR - SMOG Unemployment Gap - Smoothed.png",
    ROOT / "KR/SMOG Model/results/figures/kr_smog_unemployment_gap_filtered.png": "KR - SMOG Unemployment Gap - Filtered.png",
}


# %% US MCT chart
# Rebuild the MCT summary with the same typography, colours and open-frame style.
def build_mct_chart():
    model = ROOT / "USA/Inflation Model/mct_model"
    result = pd.read_csv(
        model / "results/python/current_reconstruction_d3000_b3000_t2_s2022_labelled.csv",
        index_col=0,
        parse_dates=True,
    )
    reference = pd.read_csv(
        model / "data/reference_202310.csv",
        index_col=0,
        parse_dates=True,
    )

    fig, ax = style.figure(title="United States: Multivariate Core Trend (MCT)")
    ax.fill_between(
        result.index,
        result["lower_16.67pct"],
        result["upper_83.33pct"],
        color=style.ACCENT,
        alpha=0.14,
    )
    ax.plot(result.index, result["MCT_median"], **style.line(0))
    ax.plot(reference.index, reference["median"], **style.line(1, lw=1.6))
    ax.axhline(2, color=style.DESERT, lw=1.3, ls=":")
    ax.annotate(
        "2% PCE inflation target", xy=(result.index[0], 2),
        xytext=(8, 7), textcoords="offset points",
        color=style.DESERT, fontsize=11, ha="left",
    )
    style.label(
        ax, result.index[-1], result["MCT_median"].iloc[-1],
        "Current reconstruction", 0, dx=10, dy=10, ha="left",
    )
    fig.text(
        0.01, 0.01,
        "Shading: central 66.7% posterior interval  |  Grey line: NY Fed, October 2023 vintage",
        color=style.NOTE, fontsize=11,
    )
    style.finish(
        fig, ax, ylabel="Annualized inflation, per cent",
        yfmt="{x:,.1f}", year_step=10,
    )
    low, high = ax.get_xlim()
    ax.set_xlim(low, high + 0.08 * (high - low))
    fig.savefig(
        OUTPUT / "USA - MCT Core Inflation.png",
        dpi=200, facecolor="white", bbox_inches="tight",
    )
    plt.close(fig)


# %% US MCT filtered chart
# Build the one-sided estimate separately and retain the smoother as a comparator.
def build_mct_filtered_chart():
    model = ROOT / "USA/Inflation Model/mct_model"
    filtered_path = (
        model
        / "results/python/current_reconstruction_d3000_b3000_t2_s2022_filtered_labelled.csv"
    )
    if not filtered_path.is_file():
        return False
    smoothed = pd.read_csv(
        model / "results/python/current_reconstruction_d3000_b3000_t2_s2022_labelled.csv",
        index_col=0,
        parse_dates=True,
    )
    filtered = pd.read_csv(filtered_path, index_col=0, parse_dates=True)

    fig, ax = style.figure(title="United States: Filtered Multivariate Core Trend (MCT)")
    ax.fill_between(
        filtered.index,
        filtered["lower_16.67pct"],
        filtered["upper_83.33pct"],
        color=style.ACCENT,
        alpha=0.14,
    )
    ax.plot(filtered.index, filtered["MCT_median"], **style.line(0))
    ax.plot(
        smoothed.index,
        smoothed["MCT_median"],
        color=style.GREY,
        lw=1.6,
        ls="--",
    )
    ax.axhline(2, color=style.DESERT, lw=1.3, ls=":")
    ax.annotate(
        "2% PCE inflation target", xy=(filtered.index[0], 2),
        xytext=(8, 7), textcoords="offset points",
        color=style.DESERT, fontsize=11, ha="left",
    )
    style.label(
        ax, filtered.index[-1], filtered["MCT_median"].iloc[-1],
        "Filtered estimate", 0, dx=10, dy=10, ha="left",
    )
    fig.text(
        0.01, 0.01,
        "Shading: filtered central 66.7% posterior interval  |  Grey dashed line: smoothed estimate",
        color=style.NOTE, fontsize=11,
    )
    style.finish(
        fig, ax, ylabel="Annualized inflation, per cent",
        yfmt="{x:,.1f}", year_step=10,
    )
    low, high = ax.get_xlim()
    ax.set_xlim(low, high + 0.08 * (high - low))
    fig.savefig(
        OUTPUT / "USA - MCT Core Inflation - Filtered.png",
        dpi=200, facecolor="white", bbox_inches="tight",
    )
    plt.close(fig)
    return True


# %% Gallery build
# Synchronize the latest saved charts and then create the styled US MCT chart.
def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    missing = [path for path in CHARTS if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing model charts:\n" + "\n".join(map(str, missing)))
    for source, name in CHARTS.items():
        copy2(source, OUTPUT / name)
    build_mct_chart()
    filtered_built = build_mct_filtered_chart()
    print(f"Saved {len(CHARTS) + 1 + int(filtered_built)} current model charts to {OUTPUT}")


if __name__ == "__main__":
    main()
