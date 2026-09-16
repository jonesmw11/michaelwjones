"""Generate AU SMOG output-gap, unemployment-gap, and NAIRU figures.

Run this file alone to refresh figures without rerunning the state-space model.
The model update script also calls save_figures after updating its CSVs.
"""

from pathlib import Path
from io import BytesIO
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, StrMethodFormatter
import numpy as np
import pandas as pd

import au_smog_model_generation as model_code


HERE = Path(__file__).resolve().parent.parent
RESULTS_DIR = HERE / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
SMOOTHED_FILE = RESULTS_DIR / "smog_au_python.csv"
FILTERED_FILE = RESULTS_DIR / "smog_au_filtered_states.csv"


def styled_chart(title, ylabel):
    """Use the line colours and open-frame style of Interest Rates/chartstyle.py."""
    plt.rcParams.update({"font.family": "Gill Sans MT", "font.size": 13,
                         "axes.unicode_minus": False})
    fig, ax = plt.subplots(figsize=(11, 6.6))
    ax.set_title(title, fontsize=17, loc="left", pad=18, color="#1A1A1A")
    ax.set_ylabel(ylabel, fontsize=12, color="#5A5A5A")
    ax.grid(axis="y", color="#EFEFEF", linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#C8C8C8")
    ax.tick_params(length=0, colors="#6A6A6A")
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    fig.subplots_adjust(left=0.09, right=0.94, top=0.88, bottom=0.12)
    return fig, ax


def save_chart(fig, path):
    """Write a rendered PNG, retrying transient Windows file-sharing errors."""
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    for attempt in range(10):
        try:
            path.write_bytes(buffer.getvalue())
            print(f"Saved {path}")
            return
        except OSError:
            if attempt == 9:
                raise
            time.sleep(0.2)


def place_labels(fig, ax, sample_end):
    ax.legend(loc="upper right", frameon=False, fontsize=12)
    fig.text(0.94, 0.055, sample_end, ha="right", va="bottom",
             color="#6A6A6A", fontsize=10)


def save_figures(out, observed_unemployment, estimate_type):
    """Render three charts for smoothed or filtered states."""
    if estimate_type not in {"smoothed", "filtered"}:
        raise ValueError(f"Unknown estimate type: {estimate_type}")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    dates = out.index.to_timestamp()
    sample_end = f"Through {out.index[-1]}"

    gap = out["output_gap"]
    fig, ax = styled_chart(
        f"Australia: unemployment-implied output gap ({estimate_type})",
        "Per cent of potential",
    )
    ax.plot(dates, gap.to_numpy(), color="#0B6E4F", linewidth=2.6,
            label="Output gap")
    limit = max(abs(gap.min()), abs(gap.max()))
    step = 2.0 if limit < 9 else 4.0
    bound = np.ceil(limit / step) * step + step
    ax.set_ylim(-bound, bound)
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.axhline(0, color="#888888", linewidth=1.4, zorder=1)
    ax.set_xlim(dates[0], dates[-1])
    place_labels(fig, ax, sample_end)
    path = FIGURES_DIR / f"au_smog_output_gap_{estimate_type}.png"
    save_chart(fig, path)

    actual = observed_unemployment.reindex(out.index)
    nairu = out["u_star"]
    if actual.isna().any():
        raise ValueError("Cannot chart NAIRU: actual unemployment is missing")
    fig, ax = styled_chart(
        f"Australia: unemployment and the NAIRU ({estimate_type})", "Per cent"
    )
    ax.plot(dates, actual.to_numpy(), color="#9A9A9A", linewidth=2.0,
            label="Unemployment")
    ax.plot(dates, nairu.to_numpy(), color="#0B6E4F", linewidth=2.6,
            label="NAIRU")
    top = float(max(actual.max(), nairu.max()))
    ax.set_ylim(-0.5, np.ceil(top / 2) * 2 + 2)
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.axhline(0, color="#888888", linewidth=1.4, zorder=1)
    ax.set_xlim(dates[0], dates[-1])
    place_labels(fig, ax, sample_end)
    path = FIGURES_DIR / f"au_smog_unemployment_and_nairu_{estimate_type}.png"
    save_chart(fig, path)

    # Use the output-gap-aligned sign: slack is negative, tightness positive.
    unemployment_gap = nairu - actual
    fig, ax = styled_chart(
        f"Australia: unemployment gap ({estimate_type})",
        "Percentage points",
    )
    ax.plot(dates, unemployment_gap.to_numpy(), color="#0B6E4F",
            linewidth=2.6, label="Unemployment gap")
    limit = float(unemployment_gap.abs().max())
    step = 1.0 if limit < 4 else 2.0
    bound = np.ceil(limit / step) * step + step
    ax.set_ylim(-bound, bound)
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.axhline(0, color="#888888", linewidth=1.4, zorder=1)
    ax.set_xlim(dates[0], dates[-1])
    place_labels(fig, ax, sample_end)
    path = FIGURES_DIR / f"au_smog_unemployment_gap_{estimate_type}.png"
    save_chart(fig, path)


def load_states(path):
    out = pd.read_csv(path)
    required = {"date", "output_gap", "y_star", "u_star"}
    if not required.issubset(out.columns):
        raise ValueError(f"{path} is missing model-state columns")
    out["date"] = pd.PeriodIndex(out["date"], freq="Q")
    out = out.set_index("date")
    if out.empty or not out.index.is_unique or not np.isfinite(out[list(required - {"date"})]).all().all():
        raise ValueError(f"{path} contains invalid model states")
    return out


def main():
    raw = pd.read_excel(
        model_code.INPUTS_XLSX, sheet_name=model_code.UPDATE_SHEET,
        usecols=["date", "unemployment"],
    )
    raw = raw.loc[raw["date"].notna()].copy()
    raw["date"] = pd.PeriodIndex(pd.to_datetime(raw["date"]), freq="Q")
    observed = pd.to_numeric(
        raw.drop_duplicates("date").set_index("date")["unemployment"],
        errors="coerce",
    )
    for estimate_type, path in (("smoothed", SMOOTHED_FILE),
                                ("filtered", FILTERED_FILE)):
        save_figures(load_states(path), observed, estimate_type)


if __name__ == "__main__":
    main()
