# Generate JP SMOG output-gap, unemployment-gap, and NAIRU figures.
#
# Run this file alone to refresh figures without rerunning the state-space model.
# The model update script also calls save_figures after updating its CSVs.

# %% Imports and file paths
# Load plotting dependencies and locate JP SMOG results.
from pathlib import Path
import sys
from io import BytesIO
import time

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, StrMethodFormatter
import numpy as np
import pandas as pd

# Keep the import and paths usable when running cells without __file__.
try:
    CODE_DIR = Path(__file__).resolve().parent
except NameError:
    CODE_DIR = next(
        (candidate for parent in (Path.cwd(), *Path.cwd().parents)
         for candidate in (
             parent / "code",
             parent / "macro-work" / "JP SMOG Model" / "code",
             parent / "michaelwjones" / "macro-work" / "JP SMOG Model" / "code",
         ) if (candidate / "jp_smog_model_generation.py").is_file()),
        None,
    )
    if CODE_DIR is None:
        raise FileNotFoundError("Open the JP SMOG Model repository folder before running cells")
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
import jp_smog_model_generation as model_code

HERE = CODE_DIR.parent
RESULTS_DIR = HERE / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
SMOOTHED_FILE = RESULTS_DIR / "smog_jp_python.csv"
FILTERED_FILE = RESULTS_DIR / "smog_jp_filtered_states.csv"


# %% Chart styling
# Set the shared typography, axes, colours, and figure size.
def styled_chart(title, ylabel):
    # Set shared chart styling.
    plt.rcParams.update({"font.family": "Gill Sans MT", "font.size": 13,
                         "axes.unicode_minus": False})
    # Create shared canvas.
    fig, ax = plt.subplots(figsize=(11, 6.6))
    ax.set_title(title, fontsize=17, loc="left", pad=18, color="#1A1A1A")
    ax.set_ylabel(ylabel, fontsize=12, color="#5A5A5A")
    ax.grid(axis="y", color="#EFEFEF", linewidth=1)
    ax.set_axisbelow(True)
    # Remove crowded borders.
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#C8C8C8")
    ax.tick_params(length=0, colors="#6A6A6A")
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    fig.subplots_adjust(left=0.09, right=0.94, top=0.88, bottom=0.12)
    return fig, ax


# %% Chart export
# Render the figure to PNG and retry temporary file-sharing failures.
def save_chart(fig, path):
    # Save chart as PNG.
    # Render chart in memory.
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    # Retry locked output files.
    for attempt in range(10):
        try:
            path.write_bytes(buffer.getvalue())
            print(f"Saved {path}")
            return
        except OSError:
            if attempt == 9:
                raise
            time.sleep(0.2)


# %% Chart labels
# Place the legend and sample-end label outside the data lines.
def place_labels(fig, ax, sample_end):
    ax.legend(loc="upper right", frameon=False, fontsize=12)
    fig.text(0.94, 0.055, sample_end, ha="right", va="bottom",
             color="#6A6A6A", fontsize=10)


# %% Figure generation
# Draw the output-gap, unemployment, and unemployment-gap charts.
def save_figures(smoothed, filtered, observed_unemployment):
    # Plot reported model states.
    # Check compatible inputs.
    if not smoothed.index.equals(filtered.index):
        raise ValueError("Smoothed and filtered states must have matching quarters")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    dates = smoothed.index.to_timestamp()
    sample_end = f"Through {smoothed.index[-1]}"

    # Plot output gap.
    fig, ax = styled_chart(
        "Japan: unemployment-implied output gap",
        "Per cent of potential",
    )
    ax.plot(dates, smoothed["output_gap"].to_numpy(), color="#0B6E4F",
            linewidth=2.6, label="Smoothed output gap")
    ax.plot(dates, filtered["output_gap"].to_numpy(), color="#5BAE95",
            linewidth=1.8, linestyle="--", label="Filtered output gap")
    limit = max(smoothed["output_gap"].abs().max(),
                filtered["output_gap"].abs().max())
    step = 2.0 if limit < 9 else 4.0
    bound = np.ceil(limit / step) * step + step
    ax.set_ylim(-bound, bound)
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.axhline(0, color="#888888", linewidth=1.4, zorder=1)
    ax.set_xlim(dates[0], dates[-1])
    place_labels(fig, ax, sample_end)
    save_chart(fig, FIGURES_DIR / "jp_smog_output_gap.png")

    actual = observed_unemployment.reindex(smoothed.index)
    if actual.isna().any():
        raise ValueError("Cannot chart NAIRU: actual unemployment is missing")
    # Plot unemployment and NAIRU.
    fig, ax = styled_chart(
        "Japan: unemployment and the NAIRU", "Per cent"
    )
    ax.plot(dates, actual.to_numpy(), color="#9A9A9A", linewidth=2.0,
            label="Unemployment")
    ax.plot(dates, smoothed["u_star"].to_numpy(), color="#0B6E4F",
            linewidth=2.6, label="Smoothed NAIRU")
    ax.plot(dates, filtered["u_star"].to_numpy(), color="#5BAE95",
            linewidth=1.8, linestyle="--", label="Filtered NAIRU")
    top = float(max(actual.max(), smoothed["u_star"].max(),
                    filtered["u_star"].max()))
    ax.set_ylim(-0.5, np.ceil(top / 2) * 2 + 2)
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.axhline(0, color="#888888", linewidth=1.4, zorder=1)
    ax.set_xlim(dates[0], dates[-1])
    place_labels(fig, ax, sample_end)
    save_chart(fig, FIGURES_DIR / "jp_smog_unemployment_and_nairu.png")

    # Match output-gap sign.
    smoothed_gap = smoothed["u_star"] - actual
    filtered_gap = filtered["u_star"] - actual
    # Plot unemployment gap.
    fig, ax = styled_chart(
        "Japan: unemployment gap",
        "Percentage points",
    )
    ax.plot(dates, smoothed_gap.to_numpy(), color="#0B6E4F",
            linewidth=2.6, label="Smoothed unemployment gap")
    ax.plot(dates, filtered_gap.to_numpy(), color="#5BAE95",
            linewidth=1.8, linestyle="--", label="Filtered unemployment gap")
    limit = float(max(smoothed_gap.abs().max(), filtered_gap.abs().max()))
    step = 1.0 if limit < 4 else 2.0
    bound = np.ceil(limit / step) * step + step
    ax.set_ylim(-bound, bound)
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.axhline(0, color="#888888", linewidth=1.4, zorder=1)
    ax.set_xlim(dates[0], dates[-1])
    place_labels(fig, ax, sample_end)
    save_chart(fig, FIGURES_DIR / "jp_smog_unemployment_gap.png")


# %% State loading
# Read saved quarterly states and prepare them for plotting.
def load_states(path):
    # Read state estimates.
    out = pd.read_csv(path)
    required = {"date", "output_gap", "y_star", "u_star"}
    # Check required columns.
    if not required.issubset(out.columns):
        raise ValueError(f"{path} is missing model-state columns")
    out["date"] = pd.PeriodIndex(out["date"], freq="Q")
    out = out.set_index("date")
    if out.empty or not out.index.is_unique or not np.isfinite(out[list(required - {"date"})]).all().all():
        raise ValueError(f"{path} contains invalid model states")
    return out


# %% Figure workflow
# Load model results and observed unemployment, then create charts.
def main():
    # Read observed unemployment.
    raw = pd.read_excel(
        model_code.INPUTS_XLSX, sheet_name=model_code.UPDATE_SHEET,
        usecols=["date", "unemployment"],
    )
    raw = raw.loc[raw["date"].notna()].copy()
    raw["date"] = pd.PeriodIndex(pd.to_datetime(raw["date"]), freq="Q")
    # Align observed unemployment.
    observed = pd.to_numeric(
        raw.drop_duplicates("date").set_index("date")["unemployment"],
        errors="coerce",
    )
    # Render updated charts.
    save_figures(load_states(SMOOTHED_FILE), load_states(FILTERED_FILE), observed)


# %% Script entry point
# Regenerate figures when this file is executed directly.
if __name__ == "__main__":
    main()
