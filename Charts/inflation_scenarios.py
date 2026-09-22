# Export fixed VAR coefficients and oil paths for the browser scenario editor.
# =============================================================================
#%% Imports
import importlib.util
import json
import sys
from functools import lru_cache
from html import escape

import numpy as np
import pandas as pd
import plotly.io as pio
from statsmodels.tsa.api import VAR

import results_dashboard_config as config

DRAWABLE_DRIVERS = {
    "oil": dict(label="Oil price", unit="USD per barrel", minimum=0.01, maximum=None, keyStep=1),
    "unemployment": dict(label="Unemployment rate", unit="Per cent", minimum=0, maximum=100, keyStep=0.1),
    "expectations": dict(label="Inflation expectations", unit="Per cent", minimum=None, maximum=None, keyStep=0.1),
}


# =============================================================================
#%% Reuse the country workbook readers and monthly model specifications
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def country_inputs(country):
    folder = config.ROOT / country / "Inflation Model"
    data = load_module(f"scenario_data_{country}", folder / "data.py")
    if country == "AU":
        quarterly = data.load_sheet("AU", "Q")
        monthly = data.load_sheet("AU-M", "M")
        drivers = quarterly[["Unemployment Rate", "Inflation expectation", "Import prices"]].copy()
        drivers.columns = ["unemployment", "expectations", "import_prices"]
        for name, column in [("oil", "Oil"), ("stage2", "Stage2")]:
            values = monthly[column].dropna()
            drivers[name] = values.groupby(values.index.asfreq("Q")).mean()
        drivers = drivers.loc["2001Q1":]
        targets = {name: quarterly[column].dropna().loc["2001Q1":].rename("cpi")
                   for name, column in {"headline": "Headline - Index", "trimmed_mean": "Trimmed mean index",
                                        "ex_food_energy": "Ex food & energy Index s.a"}.items()}
        return drivers, targets, ["cpi", "import_prices", "stage2"], 6
    previous = {name: sys.modules.get(name) for name in ("data", "varmodel")}
    try:
        sys.modules["data"] = data
        sys.modules["varmodel"] = load_module(f"scenario_var_{country}", folder / "varmodel.py")
        model = load_module(f"scenario_{country}", folder / f"{country.lower()}.py")
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    measures = (model.NATIONAL | model.TOKYO) if country == "JP" else (model.CPI_MEASURES | model.PPI_MEASURES)
    drivers = data.build_frame(model.DRIVERS, freq="M", start=model.START)
    targets = {name: data.series("JN" if country == "JP" else "KR", "M", column, name="cpi").loc[model.START:]
               for name, column in measures.items()}
    changes = ["cpi", "import_prices"] + (["stage2"] if country == "JP" else [])
    return drivers, targets, changes, 12


# =============================================================================
#%% Fit exactly the existing specifications and check against saved forecasts
def scenario_payload(country, spec):
    drivers, targets, changes, maxlags = country_inputs(country)
    saved = pd.read_csv(spec["path"], index_col=0)
    saved.index = pd.PeriodIndex(saved.index, freq=spec["frequency"])
    models = []
    for column, label in spec["series"].items():
        name = column.removesuffix("_yoy")
        target = targets[name]
        frame = pd.concat([target, drivers], axis=1).dropna()
        frame[changes] = 100 * frame[changes].pct_change(fill_method=None)
        frame = frame.dropna()
        expected = pd.period_range(frame.index[0], frame.index[-1], freq=spec["frequency"])
        if not frame.index.equals(expected):
            raise ValueError(f"Non-contiguous VAR sample: {country} {name}")
        fit = VAR(frame.to_numpy()).fit(maxlags=maxlags, ic="aic")
        steps = spec["forecast_steps"]
        baseline = (fit.forecast(frame.to_numpy()[-fit.k_ar:], steps) if fit.k_ar
                    else np.tile(fit.intercept, (steps, 1)))
        dates = pd.period_range(frame.index[-1] + 1, periods=steps, freq=spec["frequency"])
        year = 4 if spec["frequency"] == "Q" else 12
        history = target.loc[:frame.index[-1]].dropna()
        levels = pd.concat([history, pd.Series(history.iloc[-1] * np.cumprod(1 + baseline[:, 0] / 100), index=dates)])
        yoy = 100 * (levels / levels.shift(year) - 1)
        # Never attach new coefficients to a stale or differently dated saved baseline.
        np.testing.assert_allclose(yoy.loc[dates], saved.loc[dates, column], atol=1e-8, rtol=1e-8,
                                   err_msg=f"Refresh saved {country} {name} forecasts before building scenarios")
        oil = drivers["oil"].loc[:frame.index[-1]].dropna()
        oil_index = frame.columns.get_loc("oil")
        oil_path = baseline[:, oil_index]
        if not np.isfinite(oil_path).all() or (oil_path <= 0).any():
            raise ValueError(f"Non-positive baseline oil path: {country} {name}")
        drawable = {}
        for driver, metadata in DRAWABLE_DRIVERS.items():
            if driver not in frame:
                continue
            if country == "JP" and driver == "expectations":
                metadata = dict(metadata, label="Tankan expectations", unit="Per cent, 1 year ahead")
            driver_history = drivers[driver].loc[:frame.index[-1]].dropna().iloc[-60:]
            index = frame.columns.get_loc(driver)
            drawable[driver] = dict(metadata, index=index, baseline=baseline[:, index].tolist(),
                                    dates=driver_history.index.to_timestamp().strftime("%Y-%m-%d").tolist(),
                                    history=driver_history.tolist(), last=float(driver_history.iloc[-1]))
        models.append(dict(
            label=label, dates=dates.to_timestamp().strftime("%Y-%m-%d").tolist(), periods=dates.astype(str).tolist(),
            coefficients=fit.coefs.tolist(), intercept=fit.intercept.tolist(),
            seed=frame.to_numpy()[-max(1, fit.k_ar):].tolist(), oilIndex=oil_index,
            oilLast=float(oil.iloc[-1]), oilBaseline=oil_path.tolist(), baseline=baseline.tolist(),
            cpiHistory=history.iloc[-year:].tolist(), year=year, baselineYoy=yoy.loc[dates].tolist(),
            oilDates=oil.iloc[-60:].index.to_timestamp().strftime("%Y-%m-%d").tolist(),
            oilHistory=oil.iloc[-60:].tolist(), lastDate=str(frame.index[-1].to_timestamp().date()),
            lastYoy=float(yoy.loc[frame.index[-1]]), lastPeriod=str(frame.index[-1]), lag=fit.k_ar, drivers=drawable,
        ))
    return models


# =============================================================================
#%% Embed the editor with its data so GitHub Pages needs no model server
def scenario_html(country, spec, figure, include_plotlyjs):
    models = scenario_payload(country, spec)
    key = spec["path"].stem
    if country == "AU":
        figure.add_hrect(y0=2, y1=3, fillcolor="#0B6E4F", opacity=0.10,
                         line_width=0, layer="below",
                         annotation_text="2–3% target", annotation_position="top left",
                         annotation_font=dict(size=10, color="#0B6E4F"))
    elif country in {"JP", "KR"}:
        figure.add_hline(y=2, line_color="#0B6E4F", line_dash="dot", line_width=1.4,
                         annotation_text="2% CPI target", annotation_position="top left",
                         annotation_font=dict(size=10, color="#0B6E4F"))
    figure.update_xaxes(range=[str(pd.Timestamp(models[0]["lastDate"]) - pd.DateOffset(years=3)), models[0]["dates"][-1]],
                        rangeselector=dict(visible=False))
    figure.update_layout(height=420, margin=dict(l=55, r=18, t=70, b=40),
                         legend=dict(font=dict(size=11), x=0, xanchor="left", y=1.03))
    chart = pio.to_html(figure, full_html=False, include_plotlyjs=include_plotlyjs,
                        div_id=f"{key}-inflation", config={"responsive": True, "displaylogo": False})
    unit = "quarter" if spec["frequency"] == "Q" else "month"
    cards = []
    for name, driver in models[0]["drivers"].items():
        cards.append(
            f'<section class="driver-card" data-driver="{name}"><h5>{escape(driver["label"])}</h5>'
            f'<p class="driver-unit">{escape(driver["unit"])}</p>'
            f'<div class="oil-drag-container"><div id="{key}-{name}" class="plotly-graph-div"></div>'
            '<div class="oil-drag-handles"></div></div>'
            '<button type="button" data-role="reset-driver">Reset path</button>'
            '<details class="driver-exact"><summary>Exact values</summary><div class="scenario-controls">'
            '<label>Forecast period <select data-role="period"></select></label>'
            f'<label>{escape(driver["label"])} <input data-role="price" type="number" step="0.01" required></label>'
            '<button type="button" data-role="apply">Apply value</button></div></details></section>'
        )
    availability = ('<p class="scenario-method">Tankan: general-price expectations one year ahead, all enterprises and industries. '
                    'Quarterly readings carry forward from the following month. The estimation sample starts in 2014.</p>'
                    if country == "JP" else "")
    return (
        f'<article class="chart-block oil-scenario" id="{key}" data-country="{country}">'
        f'<h3>{escape(spec["title"])}</h3><p>{escape(spec["description"])}</p>'
        '<div class="scenario-columns"><section class="scenario-forecast"><h4>Inflation forecast</h4>'
        f'{chart}</section><section class="scenario-editor"><h4>Draw driver paths</h4>'
        '<p class="driver-legend"><span class="legend-observed">Observed</span> · '
        '<span class="legend-baseline">Original forecast</span> · <span class="legend-scenario">Drawn scenario</span></p>'
        f'<div class="driver-mini-grid" style="--driver-count:{len(cards)}">{"".join(cards)}</div>'
        f'<p>Draw across the shaded future area of any chart. Each stroke sets the {unit}s it crosses. '
        'All paths stay visible and combine to update the inflation forecasts.</p>'
        '<button type="button" data-role="reset">Reset country forecasts</button>'
        '<p data-role="status" role="status" aria-live="polite"></p>'
        f'{availability}</section></div>'
        '<p class="scenario-method">Coefficients stay fixed. Oil uses price levels; unemployment and expectations use percentages. '
        'Drawn paths apply together to every measure for this country, including companion charts. For each edited driver, '
        'undrawn dates retain each model’s original forecast. Other drivers evolve recursively. Effects enter through lags; '
        'these are mechanical scenarios, not identified causal shocks. Reset restores the original forecasts.</p>'
        f'<script type="application/json" class="scenario-data">{json.dumps(models, allow_nan=False)}</script></article>'
    )
