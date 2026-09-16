# Regenerate the five country forecast charts from the saved CSV results.
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import chartstyle as style


ROOT = Path(__file__).resolve().parent
CHARTS = {
    "Australia": [
        ("au_inflation_forecast.csv", "au_inflation_forecast.png", "Q", 12,
         "Australia: CPI inflation and forecast", "2010Q1",
         {"headline": "Headline", "trimmed_mean": "Trimmed mean",
          "ex_food_energy": "Ex food & energy"}),
    ],
    "Japan": [
        ("jp_cpi_inflation_forecast.csv", "jp_cpi_inflation_forecast.png", "M", 36,
         "Japan: national CPI inflation and forecast", "2010-01",
         {"headline": "Headline", "ex_fresh_food": "Ex fresh food",
          "ex_fresh_food_energy": "Ex fresh food & energy",
          "ex_food_energy": "Ex food & energy"}),
        ("jp_tokyo_inflation_forecast.csv", "jp_tokyo_inflation_forecast.png", "M", 36,
         "Japan: Tokyo CPI inflation and forecast", "2010-01",
         {"tokyo_headline": "Headline", "tokyo_ex_fresh_food": "Ex fresh food",
          "tokyo_ex_fresh_food_energy": "Ex fresh food & energy"}),
    ],
    "Korea": [
        ("kr_cpi_inflation_forecast.csv", "kr_cpi_inflation_forecast.png", "M", 36,
         "Korea: CPI inflation and forecast", "2010-01",
         {"headline": "Headline", "core": "Core (ex food & energy)"}),
        ("kr_ppi_inflation_forecast.csv", "kr_ppi_inflation_forecast.png", "M", 36,
         "Korea: PPI inflation and forecast", "2010-01",
         {"ppi": "Producer prices"}),
    ],
}


def chart(country, spec):
    csv_name, image_name, frequency, steps, title, start, series = spec
    folder = ROOT / country / "results"
    data = pd.read_csv(folder / csv_name, index_col=0)
    data.index = pd.PeriodIndex(data.index, freq=frequency)
    last_actual = data.index[-steps - 1]
    data = data.loc[pd.Period(start, freq=frequency):]

    fig, ax = style.figure(title=title)
    endpoints = []
    for i, (stem, label) in enumerate(series.items()):
        values = data[f"{stem}_yoy"].dropna()
        if values.empty:
            raise ValueError(f"No inflation values for {stem} in {csv_name}")
        actual = values.loc[:last_actual]
        projected = values.loc[last_actual:]
        colour = style.colour(i)
        ax.plot(actual.index.to_timestamp(), actual.values, color=colour, lw=2.3)
        ax.plot(projected.index.to_timestamp(), projected.values, color=colour,
                lw=2.0, ls=(0, (4, 2)))
        endpoints.append((float(values.iloc[-1]), label, i, values.index[-1].to_timestamp()))

    for rank, (value, label, i, date) in enumerate(sorted(endpoints)):
        style.label(ax, date, value, label, i, dx=9,
                    dy=(rank - (len(endpoints) - 1) / 2) * 19,
                    ha="left", bold=False)
    ax.axvline(last_actual.to_timestamp(), color="#C8C8C8", lw=0.9, ls=":")
    ax.annotate("Forecast", xy=(last_actual.to_timestamp(), 0),
                xycoords=("data", "axes fraction"), xytext=(6, 10),
                textcoords="offset points", fontsize=11, color=style.NOTE)
    style.finish(fig, ax, ylabel="Per cent, year ended", yfmt="{x:,.1f}",
                 zero_line=True, year_step=2 if frequency == "Q" else 3)
    low, high = ax.get_xlim()
    ax.set_xlim(low, high + 0.13 * (high - low))
    output = folder / "figures" / image_name
    output.parent.mkdir(exist_ok=True)
    fig.savefig(output, dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    for country, specs in CHARTS.items():
        for spec in specs:
            chart(country, spec)
