# Build the interactive portfolio results page.

# %% Imports and configuration
from html import escape
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative
import plotly.io as pio

import results_dashboard_config as config
from inflation_scenarios import scenario_html

sys.path.insert(0, str(config.MASTER_WORK["root"]))
from dashboard_charts import all_model_metrics, build_master_figures


PALETTE = [
    config.COLORS["green"],
    config.COLORS["grey"],
    config.COLORS["orange"],
    config.COLORS["blue"],
    config.COLORS["red"],
]


# %% Shared interactive chart style
def finish_figure(fig, ylabel, zero_line=False):
    fig.update_layout(
        height=520,
        margin=dict(l=72, r=28, t=20, b=45),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Gill Sans MT, Gill Sans, Arial, sans-serif", size=14,
                  color=config.COLORS["ink"]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, bgcolor="rgba(255,255,255,0)"),
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="#C8C8C8",
            rangeselector=dict(
                buttons=[
                    dict(count=5, label="5y", step="year", stepmode="backward"),
                    dict(count=10, label="10y", step="year", stepmode="backward"),
                    dict(count=20, label="20y", step="year", stepmode="backward"),
                    dict(step="all", label="All"),
                ],
                bgcolor="white",
                activecolor="#E7F2EE",
                bordercolor="#D5D5D5",
                borderwidth=1,
            ),
            rangeslider=dict(visible=True, thickness=0.07),
            type="date",
        ),
        yaxis=dict(
            title=ylabel,
            gridcolor=config.COLORS["grid"],
            zeroline=False,
            ticksuffix="",
        ),
    )
    if zero_line:
        fig.add_hline(y=0, line_color="#888888", line_width=1)
    return fig


# %% Inflation forecast charts
def inflation_figure(spec):
    data = pd.read_csv(spec["path"], index_col=0)
    data.index = pd.PeriodIndex(data.index, freq=spec["frequency"]).to_timestamp()
    split = len(data) - spec["forecast_steps"] - 1
    fig = go.Figure()
    for number, (column, label) in enumerate(spec["series"].items()):
        values = data[column].dropna()
        actual = values.loc[:data.index[split]]
        forecast = values.loc[data.index[split]:]
        colour = PALETTE[number % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=actual.index, y=actual, mode="lines", name=label,
            legendgroup=label, line=dict(color=colour, width=2.6),
            hovertemplate=f"{label}: %{{y:.2f}}%<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=forecast.index, y=forecast, mode="lines", name=f"{label} forecast",
            legendgroup=label, showlegend=False,
            line=dict(color=colour, width=2.3, dash="dash"),
            hovertemplate=f"{label} forecast: %{{y:.2f}}%<extra></extra>",
        ))
    fig.add_vline(
        x=data.index[split].timestamp() * 1000,
        line_color="#B8B8B8", line_dash="dot", line_width=1,
        annotation_text="Forecast", annotation_position="bottom right",
    )
    return finish_figure(fig, "Per cent, year ended", zero_line=True)


# =============================================================================
# %% MCT charts
def load_mct_context(spec):
    if "context" in spec:
        context = pd.read_csv(spec["context"], index_col=0, parse_dates=True)
        if "observed_core_yoy" in context and context["observed_core_yoy"].notna().any():
            return context["observed_core_yoy"].dropna()
        official = context["official_core_yoy"].dropna()
        if official.empty:
            official = context["headline_yoy"].dropna()
        return official
    prices = pd.read_csv(spec["pce_prices"], index_col="Period", parse_dates=True)
    core_price = prices[spec["core_pce_line"]]
    return 100 * (core_price / core_price.shift(12) - 1)


def mct_figure(country, state):
    spec = config.MCT_MODELS[country]
    smoothed = pd.read_csv(spec["result"], index_col=0, parse_dates=True)
    if state == "filtered":
        if "filtered" not in spec or not spec["filtered"].exists():
            raise ValueError(f"Filtered MCT output is unavailable for {country}")
        result = pd.read_csv(spec["filtered"], index_col=0, parse_dates=True)
        state_label = "Filtered"
    elif state == "smoothed":
        result = smoothed
        state_label = "Smoothed"
    else:
        raise ValueError(f"Unknown MCT state: {state}")
    official = load_mct_context(spec)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result.index, y=result["upper_83.33pct"], mode="lines",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=result.index, y=result["lower_16.67pct"], mode="lines",
        line=dict(width=0), fill="tonexty", fillcolor="rgba(11,110,79,0.15)",
        name=f"{state_label} central 66.7% interval", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=result.index, y=result["MCT_median"], mode="lines",
        name=f"{state_label} MCT",
        line=dict(color=config.COLORS["green"], width=2.8),
        hovertemplate=f"{state_label} MCT: %{{y:.2f}}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=official.index, y=official, mode="lines",
        name=spec["official_label"],
        line=dict(color=config.COLORS["grey"], width=1.5),
        hovertemplate="Official/context: %{y:.2f}%<extra></extra>",
    ))
    if "target_upper" in spec:
        fig.add_hrect(
            y0=spec["target"], y1=spec["target_upper"],
            fillcolor=config.COLORS["orange"], opacity=0.09,
            line_width=0, layer="below",
        )
        fig.add_hline(y=spec["target_upper"], line_color=config.COLORS["orange"], line_dash="dot", line_width=1.3)
    fig.add_hline(
        y=spec["target"],
        line_color=config.COLORS["orange"], line_dash="dot", line_width=1.5,
        annotation_text=spec["target_label"],
        annotation_position="top left",
    )
    return finish_figure(fig, "Annualized inflation, per cent")


def mct_sector_trends_figure(country):
    spec = config.MCT_MODELS[country]
    if "sector_trends" in spec:
        sector_trends = pd.read_csv(spec["sector_trends"], index_col=0)
    else:
        sector_trends = pd.read_excel(spec["results_workbook"], sheet_name="Sector trend medians", index_col=0)
    sector_trends.index = pd.to_datetime(sector_trends.index)
    mapping = pd.read_csv(spec["sector_mapping"])
    included_in_core = mapping.set_index("name")["included_in_core"].to_dict()
    fig = go.Figure()
    for number, sector in enumerate(sector_trends.columns):
        core_sector = included_in_core[sector]
        label = sector if core_sector else f"{sector} (excluded from aggregate)"
        fig.add_trace(go.Scatter(
            x=sector_trends.index,
            y=sector_trends[sector],
            mode="lines",
            name=label,
            visible=True if sector == spec["default_sector"] else "legendonly",
            line=dict(
                color=qualitative.Alphabet[number],
                width=1.8,
                dash="solid" if core_sector else "dash",
            ),
            hovertemplate=f"{sector} trend: %{{y:.2f}}%<extra></extra>",
        ))
    fig.add_hline(
        y=spec["target"],
        line_color=config.COLORS["orange"], line_dash="dot", line_width=1.5,
        annotation_text=spec["target_label"],
        annotation_position="top left",
    )
    if "target_upper" in spec:
        fig.add_hrect(
            y0=spec["target"], y1=spec["target_upper"],
            fillcolor=config.COLORS["orange"], opacity=0.09,
            line_width=0, layer="below",
        )
        fig.add_hline(y=spec["target_upper"], line_color=config.COLORS["orange"], line_dash="dot", line_width=1.3)
    fig = finish_figure(fig, "Persistent annualized inflation, per cent")
    fig.update_layout(
        height=760,
        margin=dict(l=72, r=410, t=20, b=45),
        legend=dict(
            orientation="v", yanchor="top", y=1,
            xanchor="left", x=1.01, bgcolor="rgba(255,255,255,0)",
            font=dict(size=11),
        ),
    )
    return fig


# %% SMOG charts
def load_smog(country):
    spec = config.SMOG_MODELS[country]
    smoothed = pd.read_csv(spec["smoothed"])
    filtered = pd.read_csv(spec["filtered"])
    for frame in (smoothed, filtered):
        frame["date"] = pd.PeriodIndex(frame["date"], freq="Q")
        frame.set_index("date", inplace=True)
    raw = pd.read_excel(spec["inputs"], sheet_name="Update", usecols=["date", "unemployment"])
    raw = raw.loc[raw["date"].notna()].copy()
    raw["date"] = pd.PeriodIndex(pd.to_datetime(raw["date"]), freq="Q")
    unemployment = pd.to_numeric(
        raw.drop_duplicates("date").set_index("date")["unemployment"],
        errors="coerce",
    ).reindex(smoothed.index)
    dates = smoothed.index.to_timestamp()
    return dates, smoothed, filtered, unemployment


def smog_figures(country):
    dates, smoothed, filtered, unemployment = load_smog(country)
    figures = []

    output_gap = go.Figure()
    output_gap.add_trace(go.Scatter(
        x=dates, y=smoothed["output_gap"], mode="lines", name="Smoothed output gap",
        line=dict(color=config.COLORS["green"], width=2.8),
        hovertemplate="Smoothed: %{y:.2f}%<extra></extra>",
    ))
    output_gap.add_trace(go.Scatter(
        x=dates, y=filtered["output_gap"], mode="lines", name="Filtered output gap",
        line=dict(color=config.COLORS["green_light"], width=2, dash="dash"),
        hovertemplate="Filtered: %{y:.2f}%<extra></extra>",
    ))
    figures.append(("SMOG output gap", finish_figure(output_gap, "Per cent of potential", True)))

    nairu = go.Figure()
    nairu.add_trace(go.Scatter(
        x=dates, y=unemployment, mode="lines", name="Unemployment",
        line=dict(color=config.COLORS["grey"], width=2.2),
        hovertemplate="Unemployment: %{y:.2f}%<extra></extra>",
    ))
    nairu.add_trace(go.Scatter(
        x=dates, y=smoothed["u_star"], mode="lines", name="Smoothed NAIRU",
        line=dict(color=config.COLORS["green"], width=2.8),
        hovertemplate="Smoothed NAIRU: %{y:.2f}%<extra></extra>",
    ))
    nairu.add_trace(go.Scatter(
        x=dates, y=filtered["u_star"], mode="lines", name="Filtered NAIRU",
        line=dict(color=config.COLORS["green_light"], width=2, dash="dash"),
        hovertemplate="Filtered NAIRU: %{y:.2f}%<extra></extra>",
    ))
    figures.append(("Unemployment and NAIRU", finish_figure(nairu, "Per cent")))

    unemployment_gap = go.Figure()
    unemployment_gap.add_trace(go.Scatter(
        x=dates, y=smoothed["u_star"].to_numpy() - unemployment.to_numpy(),
        mode="lines", name="Smoothed unemployment gap",
        line=dict(color=config.COLORS["green"], width=2.8),
        hovertemplate="Smoothed gap: %{y:.2f} pp<extra></extra>",
    ))
    unemployment_gap.add_trace(go.Scatter(
        x=dates, y=filtered["u_star"].to_numpy() - unemployment.to_numpy(),
        mode="lines", name="Filtered unemployment gap",
        line=dict(color=config.COLORS["green_light"], width=2, dash="dash"),
        hovertemplate="Filtered gap: %{y:.2f} pp<extra></extra>",
    ))
    figures.append(("SMOG unemployment gap", finish_figure(unemployment_gap, "Percentage points", True)))
    return figures


# %% Master's dissertation results
def all_models_table_html(work):
    rows = all_model_metrics(work)
    body = []
    for row in rows:
        body.append(
            f'<tr class={"\"best-model\"" if row["best"] else "\"\""} '
            f'data-model="{escape(row["model"].lower())}">'
            f'<td data-value="{escape(row["model"].lower())}">{escape(row["model"])}</td>'
            f'<td data-value="{row["ape"]:.8f}">{row["ape"]:.2f}</td>'
            f'<td data-value="{row["aae"]:.8f}">{row["aae"]:.4f}</td>'
            f'<td data-value="{row["rmse"]:.8f}"><strong>{row["rmse"]:.4f}</strong></td>'
            f'<td data-value="{row["arpe"]:.8f}">{row["arpe"]:.2f}</td>'
            '</tr>'
        )
    headers = [
        ("Model", "Model name"),
        ("APE (%)", "Absolute pricing error relative to the mean market price"),
        ("AAE", "Average absolute error"),
        ("RMSE", "Root-mean-square error"),
        ("ARPE (%)", "Average relative pricing error"),
    ]
    header_html = "".join(
        f'<th scope="col"><button class="table-sort" type="button" '
        f'title="Sort by {escape(title)}">{escape(label)} <span aria-hidden="true">↕</span></button></th>'
        for label, title in headers
    )
    return (
        '<div class="all-models-controls">'
        '<label for="model-table-search">Find a model</label>'
        '<input id="model-table-search" type="search" placeholder="e.g. Gamma–OU">'
        '<span><i></i> Dissertation best-fitting group</span>'
        '</div>'
        '<div class="table-wrap">'
        '<table class="results-table" id="all-models-table">'
        f'<thead><tr>{header_html}</tr></thead><tbody>{"".join(body)}</tbody>'
        '</table></div>'
        '<p class="table-note">Click a column heading to sort. Yellow rows satisfy all four '
        'best-fitting thresholds used in Table 27.</p>'
    )


def masters_section_html(include_plotlyjs):
    work = config.MASTER_WORK
    figures = build_master_figures(work, config.COLORS)
    overview = (
        '<div class="masters-intro">'
        '<p>It is well known that the two-parameter Black–Scholes model does not adequately '
        'describe stock or index price behaviour, and is unsuitable for modelling or determining '
        'real-world option prices. Many models have been proposed by Schoutens (2003) to address '
        'these shortcomings, among them Lévy process models and stochastic volatility models. '
        'This dissertation examines how these models perform against a highly volatile index, '
        'the South Korean Composite Stock Price Index (KOSPI), using 212 call options quoted on '
        '30 July 2026. The Black–Scholes model prices these options with a root-mean-square error '
        '(RMSE) of approximately 12.36. In addition, the five Lévy models examined do not improve '
        'on it, with most calibrating to a normal distribution. Analysing implied volatility, we '
        'find that it decreases from 0.89 to 0.60 as the time to expiry T increases, so a model '
        'that allows volatility to vary across expiries is essential. Introducing stochastic '
        'volatility reduces the error to 1.77, and the five best-performing models have '
        'approximately the same RMSE. The Barndorff-Nielsen–Shephard Gamma–OU model is the most '
        'parsimonious.</p>'
        '</div>'
    )

    chart_specs = {
        "data": [
            ("KOSPI 200 call-option data", "The complete option chain used in the dissertation. All seven expiries are shown together; hover over a point for its price, maturity and implied volatility.", "option_data"),
        ],
        "black-scholes": [
            ("Black–Scholes fitted values", "Market prices and fitted values from one volatility calibrated across the complete option chain.", "black_scholes_fitted"),
            ("Market implied volatility", "All seven market volatility smiles are shown together and labelled by expiry.", "market_implied_volatility"),
            ("Per-maturity Black–Scholes fitted values", "A separate volatility is fitted to each expiry, with the complete chain shown in one chart.", "black_scholes_by_expiry"),
            ("Black–Scholes volatility term structure", "The seven expiry-specific estimates show how fitted volatility falls as time to expiry increases.", "black_scholes_term_structure"),
        ],
        "levy": [
            ("Lévy-model fitted values", "Market prices and all five calibrated Lévy-model fits across the complete option chain.", "levy_fitted"),
            ("Lévy fitted densities", "Choose any of the seven maturities to compare the fitted risk-neutral densities. The Generalized Hyperbolic density is omitted because its fitted density could not be recovered reliably.", "levy_densities"),
        ],
        "stochastic-volatility": [
            ("Fitted values of the five best models", "Market prices and fitted values from the five strongest models across the complete option chain.", "best_fitted"),
            ("Pricing errors by expiry", "Choose an expiry to compare the individual pricing-error points; observations are not joined by lines.", "best_errors"),
            ("Fitted densities of the five best models", "Choose any maturity to compare the five model-implied risk-neutral densities with the corresponding Black–Scholes normal density.", "best_densities"),
            ("Implied volatility of the best models", "Annualized volatility from each model’s fitted return distribution, matching the calculation used in the original dissertation figure.", "best_implied_volatility"),
        ],
    }
    panels = {}
    section_summaries = {
        "black-scholes": (
            "Black–Scholes mispriced the option chain because both its normal-return assumption "
            "and its single constant-volatility assumption break down. Interestingly, the implied-"
            "volatility estimates suggest that volatility may be treated as constant within each "
            "maturity, but not across maturities. Fitting one volatility per maturity worked much "
            "better, although it remains a descriptive seven-parameter fix rather than a coherent "
            "model of how volatility evolves."
        ),
        "levy": (
            "Lévy models are designed to accommodate fat-tailed return distributions, providing "
            "greater flexibility than the normal parameter space of Black–Scholes. On this dataset, "
            "however, they failed to use that flexibility: the lowest-RMSE calibrations largely "
            "converged towards the normal distribution and therefore produced little improvement "
            "over Black–Scholes."
        ),
        "stochastic-volatility": (
            "Making volatility or time stochastic reduced RMSE from 12.36 to about 1.8. The five "
            "models shown here are the best-fitting specifications and performed approximately "
            "equally well. Introducing a second stochastic process—for volatility or for the rate "
            "at which time passes—allows the implied log-return distribution to escape normality, "
            "substantially improving the model fit. The resulting volatility curves also track the "
            "term structure revealed by the per-maturity Black–Scholes estimates. BNS Gamma–OU is "
            "the preferred parsimonious specification because it achieves this fit with fewer parameters."
        ),
    }
    for slug, specs in chart_specs.items():
        blocks = []
        if slug in section_summaries:
            blocks.append(
                f'<div class="section-summary"><p>{escape(section_summaries[slug])}</p></div>'
            )
        for title, description, figure_key in specs:
            blocks.append(chart_html(
                title, description, figures[figure_key], include_plotlyjs,
            ))
            include_plotlyjs = False
        panels[slug] = "".join(blocks)

    all_models = (
        '<div class="section-summary"><p>Table 27 brings every fitted specification together. '
        'It shows the sharp divide between the Black–Scholes and pure Lévy fits and the much '
        'stronger stochastic-volatility and stochastic-time models.</p></div>'
        f'{all_models_table_html(work)}'
    )

    method = (
        '<div class="method-intro"><p>The models differ in their assumptions about returns and '
        'volatility, but they are fitted and interpreted through the same three-step workflow.</p></div>'
        '<div class="method-grid">'
        '<article class="method-step"><span>1</span><div>'
        '<h3>Price and fit the models</h3>'
        '<p>Each model supplies a characteristic function—a compact description of the probability '
        'distribution of the future log price:</p>'
        '<div class="equation">\\[\\phi_T(u)=\\mathbb{E}\\!\\left[e^{iu\\log S_T}\\right]\\]</div>'
        '<p>The Carr–Madan method converts this characteristic function into option prices using '
        'Fourier integration. The model parameters are then chosen to minimize the root-mean-square '
        'difference between model and market prices:</p>'
        '<div class="equation">\\[\\widehat{\\theta}=\\underset{\\theta}{\\operatorname{arg\\,min}}\\;'
        '\\sqrt{\\frac{1}{n}\\sum_{i=1}^{n}\\left(C_{\\mathrm{model},i}(\\theta)'
        '-C_{\\mathrm{market},i}\\right)^2}\\]</div>'
        '<p>RMSE penalizes larger pricing errors more heavily, so the selected parameters are those '
        'that reproduce the complete option chain most closely.</p>'
        '</div></article>'
        '<article class="method-step"><span>2</span><div>'
        '<h3>Recover the fitted densities</h3>'
        '<p>After calibration, the log-price characteristic function is shifted to describe the log '
        'return \\(X_T=\\log(S_T/S_0)\\). Fourier inversion then converts it '
        'back into the fitted probability density:</p>'
        '<div class="equation">\\[f_T(x)=\\frac{1}{\\pi}\\int_0^{\\infty}'
        '\\operatorname{Re}\\!\\left[e^{-iux}\\phi_{X,T}(u)\\right]\\,du\\]</div>'
        '<p>This is why the density charts can be produced even when a model has no convenient '
        'closed-form density: its characteristic function contains the same distributional information.</p>'
        '</div></article>'
        '<article class="method-step"><span>3</span><div>'
        '<h3>Calculate fitted volatility</h3>'
        '<p>For each maturity, volatility is the annualized standard deviation of the model’s fitted '
        'log return:</p>'
        '<div class="equation">\\[\\sigma(T)=\\sqrt{\\frac{\\operatorname{Var}\\!\\left('
        '\\log(S_T/S_0)\\right)}{T}}\\]</div>'
        '<p>The variance is obtained from the second cumulant of the fitted characteristic function:</p>'
        '<div class="equation">\\[\\operatorname{Var}(X_T)=-\\left.\\frac{d^2}{du^2}'
        '\\log\\phi_{X,T}(u)\\right|_{u=0}\\]</div>'
        '<p>'
        'In the BNS model it combines the decaying initial variance, long-run jump variation and the '
        'leverage contribution. In the stochastic-time models it combines the mean and variance of '
        'the underlying Lévy process with the fitted random clock. Evaluating this expression across '
        'T produces the smooth volatility curves compared with the per-maturity Black–Scholes estimates.</p>'
        '</div></article>'
        '</div>'
    )

    tabs = [
        ("overview", "Overview", overview),
        ("data", "Data", panels["data"]),
        ("black-scholes", "Black–Scholes", panels["black-scholes"]),
        ("levy", "Lévy Models", panels["levy"]),
        ("stochastic-volatility", "Stochastic Volatility", panels["stochastic-volatility"]),
        ("method", "Method", method),
        ("all-models", "All Models", all_models),
    ]
    tab_buttons = []
    tab_panels = []
    for number, (slug, label, content) in enumerate(tabs):
        active = number == 0
        tab_id = f"masters-{slug}-tab"
        panel_id = f"masters-{slug}-panel"
        tab_buttons.append(
            f'<button class="model-tab{" active" if active else ""}" id="{tab_id}" '
            f'type="button" role="tab" aria-controls="{panel_id}" '
            f'aria-selected="{str(active).lower()}">{escape(label)}</button>'
        )
        tab_panels.append(
            f'<div class="model-panel" id="{panel_id}" role="tabpanel" '
            f'aria-labelledby="{tab_id}"{"" if active else " hidden"}>{content}</div>'
        )

    section = (
        '<section class="family-panel" id="family-masters-panel" role="tabpanel" '
        'aria-labelledby="family-masters-tab">'
        '<h2>Master’s dissertation: Option pricing</h2>'
        '<p class="family-summary">Key results from the KOSPI 200 option-pricing analysis, '
        'from the Black–Scholes benchmark through stochastic volatility and stochastic time.</p>'
        '<div class="model-tabs" role="tablist" aria-label="Master’s dissertation sections">'
        f'{"".join(tab_buttons)}</div>{"".join(tab_panels)}</section>'
    )
    return section, include_plotlyjs


# %% HTML assembly
def chart_html(title, description, figure, include_plotlyjs):
    chart = pio.to_html(
        figure,
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"responsive": True, "displaylogo": False, "scrollZoom": False},
    )
    return (
        '<article class="chart-block">'
        f'<h3>{escape(title)}</h3>'
        f'<p>{escape(description)}</p>'
        f'{chart}'
        '</article>'
    )


def country_tabs_section(slug, title, summary, country_blocks):
    tab_buttons = []
    tab_panels = []
    for number, (country, blocks) in enumerate(country_blocks.items()):
        active = number == 0
        country_name = config.COUNTRIES[country]["name"]
        tab_id = f"{slug}-{country.lower()}-tab"
        panel_id = f"{slug}-{country.lower()}-panel"
        tab_buttons.append(
            f'<button class="country-tab{" active" if active else ""}" '
            f'id="{tab_id}" type="button" role="tab" '
            f'aria-controls="{panel_id}" aria-selected="{str(active).lower()}">'
            f'{escape(country_name)}</button>'
        )
        tab_panels.append(
            f'<div class="country-panel" id="{panel_id}" role="tabpanel" '
            f'aria-labelledby="{tab_id}"{"" if active else " hidden"}>'
            f'<h3 class="country-heading">{escape(country_name)}</h3>'
            f'{"".join(blocks)}</div>'
        )
    return (
        f'<section class="family-panel" id="family-{slug}-panel" role="tabpanel" '
        f'aria-labelledby="family-{slug}-tab" hidden>'
        f'<h2>{escape(title)}</h2>'
        f'<p class="family-summary">{escape(summary)}</p>'
        f'<div class="country-tabs" role="tablist" aria-label="{escape(title)} countries">'
        f'{"".join(tab_buttons)}</div>{"".join(tab_panels)}</section>'
    )


def build_page():
    masters_section, include_plotlyjs = masters_section_html(True)
    sections = [masters_section]

    mct_blocks = {}
    for country in config.COUNTRY_ORDER:
        if country not in config.MCT_MODELS:
            continue
        country_name = config.COUNTRIES[country]["name"]
        spec = config.MCT_MODELS[country]
        blocks = []
        if "filtered" in spec and spec["filtered"].exists():
            blocks.append(chart_html(
                f"{country_name}: Filtered core MCT",
                spec["description"], mct_figure(country, "filtered"), include_plotlyjs,
            ))
            include_plotlyjs = False
        blocks.append(chart_html(
            f"{country_name}: Smoothed core MCT",
            spec["description"], mct_figure(country, "smoothed"), include_plotlyjs,
        ))
        include_plotlyjs = False
        blocks.append(chart_html(
            f"{country_name}: Persistent sector trends",
            spec["sector_trends_description"],
            mct_sector_trends_figure(country), include_plotlyjs,
        ))
        if country == "AU" and "AU_HEADLINE" in config.MCT_MODELS:
            headline = config.MCT_MODELS["AU_HEADLINE"]
            blocks.append(chart_html(
                "Australia: Filtered headline MCT",
                headline["description"],
                mct_figure("AU_HEADLINE", "filtered"), include_plotlyjs,
            ))
            blocks.append(chart_html(
                "Australia: Smoothed headline MCT",
                headline["description"],
                mct_figure("AU_HEADLINE", "smoothed"), include_plotlyjs,
            ))
            blocks.append(chart_html(
                "Australia: Persistent headline-sector trends",
                headline["sector_trends_description"],
                mct_sector_trends_figure("AU_HEADLINE"), include_plotlyjs,
            ))
        mct_blocks[country] = blocks
    sections.append(country_tabs_section(
        "mct",
        "MCT modelling",
        "Multivariate Core Trend models estimate persistent inflation using detailed price sectors. Each country tab contains filtered and smoothed aggregate estimates where available, posterior uncertainty, observed inflation context and persistent sector trends.",
        mct_blocks,
    ))

    smog_blocks = {}
    for country in config.COUNTRY_ORDER:
        if country not in config.SMOG_MODELS:
            continue
        spec = config.SMOG_MODELS[country]
        blocks = []
        for title, figure in smog_figures(country):
            blocks.append(chart_html(title, spec["description"], figure, include_plotlyjs))
            include_plotlyjs = False
        smog_blocks[country] = blocks
    sections.append(country_tabs_section(
        "smog",
        "SMOG state-space modelling",
        "SMOG stands for Small Multivariate Output Gap. These state-space models combine economic relationships and signal equations to estimate potential output, the output gap and the NAIRU.",
        smog_blocks,
    ))

    var_blocks = {}
    for country in config.COUNTRY_ORDER:
        models = config.INFLATION_MODELS[country]
        if not models:
            continue
        blocks = []
        for model in models:
            blocks.append(scenario_html(
                country, model,
                inflation_figure(model), include_plotlyjs,
            ))
            include_plotlyjs = False
        var_blocks[country] = blocks
    sections.append(country_tabs_section(
        "var",
        "Inflation VAR modelling",
        "Vector autoregression models project inflation jointly with domestic and external drivers. Country tabs separate the quarterly Australian system from the monthly Japanese and South Korean systems.",
        var_blocks,
    ))

    family_tabs = [
        ("masters", "Master’s Work"),
        ("mct", "MCT Modelling"),
        ("smog", "SMOG State Space"),
        ("var", "Inflation VAR"),
    ]
    nav = "".join(
        f'<button class="family-tab{" active" if number == 0 else ""}" '
        f'id="family-{slug}-tab" type="button" role="tab" '
        f'aria-controls="family-{slug}-panel" '
        f'aria-selected="{str(number == 0).lower()}" data-family="{slug}">'
        f'{escape(label)}</button>'
        for number, (slug, label) in enumerate(family_tabs)
    )
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research results</title>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js"></script>
<style>
:root {{ --green:#0B6E4F; --ink:#1A1A1A; --note:#5A5A5A; --line:#E4E4E4; --soft:#F5F8F7; }}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0; color:var(--ink); background:white; font-family:"Gill Sans MT","Gill Sans",Arial,sans-serif; }}
header {{ max-width:1180px; margin:0 auto; padding:42px 28px 24px; }}
h1 {{ margin:0 0 10px; font-size:34px; font-weight:500; }}
header p, .family-summary, .chart-block p {{ color:var(--note); line-height:1.55; }}
.family-tabs {{ position:sticky; top:0; z-index:10; display:flex; gap:8px; flex-wrap:wrap; padding:12px max(28px, calc((100vw - 1180px)/2 + 28px)); background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); }}
.family-tab, .country-tab, .model-tab {{ appearance:none; color:var(--note); background:transparent; border:0; font:inherit; font-weight:500; cursor:pointer; }}
.family-tab {{ padding:8px 13px; border-radius:4px; }}
.family-tab:hover, .family-tab.active {{ color:var(--green); background:var(--soft); }}
main {{ max-width:1180px; margin:0 auto; padding:0 28px 60px; }}
.family-panel {{ padding-top:34px; }}
h2 {{ margin:0 0 8px; font-size:28px; font-weight:500; border-bottom:2px solid var(--green); padding-bottom:8px; }}
.family-summary {{ max-width:960px; }}
.country-tabs {{ display:flex; gap:22px; flex-wrap:wrap; margin-top:22px; border-bottom:1px solid var(--line); }}
.country-tab {{ padding:9px 2px 8px; border-bottom:3px solid transparent; }}
.country-tab:hover, .country-tab.active {{ color:var(--green); border-bottom-color:var(--green); }}
.country-panel {{ padding-top:24px; }}
.country-heading {{ margin:0 0 8px; font-size:22px; font-weight:500; }}
.model-tabs {{ display:flex; gap:24px; flex-wrap:wrap; margin-top:22px; border-bottom:1px solid var(--line); }}
.model-tab {{ padding:9px 2px 8px; border-bottom:3px solid transparent; }}
.model-tab:hover, .model-tab.active {{ color:var(--green); border-bottom-color:var(--green); }}
.model-panel {{ padding-top:1px; }}
.empty-state {{ margin:30px 0; color:var(--note); }}
.chart-block {{ margin:26px 0 46px; }}
main:has(#family-var-panel:not([hidden])) {{ max-width:1600px; }}
.scenario-columns {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:20px; align-items:start; margin-top:20px; }}
.scenario-columns > section {{ min-width:0; padding:12px; border:1px solid var(--line); border-radius:5px; }}
.scenario-columns h4 {{ margin:4px 0 6px; font-size:19px; font-weight:500; }}
.scenario-editor {{ background:var(--soft); }}
.scenario-driver-label {{ display:flex; align-items:center; gap:10px; margin:8px 0; font-size:14px; }}
.scenario-driver-label select {{ font:inherit; padding:7px; border:1px solid #BBB; border-radius:4px; background:white; max-width:100%; }}
@media (max-width:800px) {{ .scenario-columns {{ grid-template-columns:minmax(0,1fr); }} }}
.scenario-controls {{ display:flex; gap:12px; flex-wrap:wrap; align-items:end; margin:18px 0; }}
.scenario-controls label {{ display:grid; gap:6px; font-size:14px; }}
.scenario-controls input, .scenario-controls select, .scenario-controls button {{ padding:9px; font:inherit; border:1px solid #BBB; border-radius:4px; background:white; }}
.scenario-controls input {{ width:160px; }}
.scenario-controls button {{ cursor:pointer; color:var(--green); }}
.scenario-method {{ font-size:13px; margin-top:12px !important; }}
.scenario-editor [data-role="status"] {{ height:5em; overflow-y:auto; font-size:14px; }}
.oil-drag-container {{ position:relative; }}
.oil-drag-handles {{ position:absolute; inset:0; pointer-events:none; }}
.oil-draw-surface {{ position:absolute; pointer-events:auto; touch-action:none; cursor:crosshair; background:rgba(181,101,29,.06); border-left:1px dashed #B5651D; }}
.oil-handle {{ position:absolute; width:8px; height:8px; border:1px solid white; border-radius:50%; background:#B5651D; transform:translate(-50%,-50%); pointer-events:none; padding:0; }}
.oil-handle:hover, .oil-handle:focus-visible {{ outline:3px solid #B5651D; outline-offset:2px; }}
h3 {{ margin:0 0 6px; font-size:21px; font-weight:500; }}
.chart-block p {{ margin:0 0 8px; max-width:900px; }}
.plotly-graph-div {{ width:100% !important; }}
.masters-intro {{ max-width:900px; padding:24px 0 8px; color:var(--note); line-height:1.55; }}
.masters-intro a {{ color:var(--green); }}
.section-summary {{ max-width:920px; margin:24px 0 10px; padding:16px 19px; color:var(--note); line-height:1.55; background:var(--soft); border-left:4px solid var(--green); }}
.section-summary p {{ margin:0; }}
.method-intro {{ max-width:900px; margin:24px 0 18px; color:var(--note); line-height:1.55; }}
.method-grid {{ display:grid; gap:18px; }}
.method-step {{ display:grid; grid-template-columns:42px minmax(0,1fr); gap:15px; padding:21px; border:1px solid var(--line); border-radius:5px; }}
.method-step > span {{ display:flex; align-items:center; justify-content:center; width:34px; height:34px; color:white; background:var(--green); border-radius:50%; font-weight:600; }}
.method-step h3 {{ margin:3px 0 9px; }}
.method-step p {{ max-width:900px; margin:8px 0; color:var(--note); line-height:1.55; }}
.equation {{ margin:14px 0; padding:15px 18px; overflow-x:auto; color:var(--ink); background:#FAFAFA; border-left:3px solid #C8DCD5; font-size:19px; text-align:center; }}
.equation mjx-container {{ margin:0 !important; min-width:max-content; }}
.all-models-controls {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin:24px 0 12px; color:var(--note); }}
.all-models-controls label {{ color:var(--ink); font-weight:500; }}
.all-models-controls input {{ min-width:230px; padding:8px 10px; border:1px solid #CFCFCF; border-radius:4px; font:inherit; }}
.all-models-controls span {{ margin-left:auto; display:flex; align-items:center; gap:7px; }}
.all-models-controls i {{ width:18px; height:13px; background:#FFF2A8; border:1px solid #E8D26D; }}
.table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:4px; }}
.results-table {{ width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }}
.results-table th {{ background:#F6F6F6; border-bottom:2px solid #CFCFCF; text-align:right; }}
.results-table th:first-child, .results-table td:first-child {{ text-align:left; }}
.results-table td {{ padding:10px 14px; text-align:right; border-bottom:1px solid var(--line); }}
.results-table tbody tr:last-child td {{ border-bottom:0; }}
.results-table tbody tr:hover td {{ box-shadow:inset 0 0 0 9999px rgba(11,110,79,.06); }}
.results-table .best-model td {{ background:#FFF2A8; }}
.results-table .best-model:hover td {{ box-shadow:inset 0 0 0 9999px rgba(230,159,0,.12); }}
.table-sort {{ width:100%; padding:11px 14px; color:var(--ink); background:transparent; border:0; font:inherit; font-weight:500; text-align:inherit; cursor:pointer; }}
.table-sort:hover {{ color:var(--green); }}
.table-note {{ color:var(--note); font-size:13px; }}
footer {{ max-width:1180px; margin:0 auto; padding:0 28px 40px; color:var(--note); }}
@media (max-width:640px) {{ header, main, footer {{ padding-left:16px; padding-right:16px; }} .family-tabs {{ padding-left:12px; }} h1 {{ font-size:28px; }} .method-step {{ grid-template-columns:1fr; }} .all-models-controls span {{ margin-left:0; }} }}
</style>
</head>
<body>
<header>
<h1>Research results</h1>
<p>Explore the research by modelling framework, then select a country within each macroeconomic model family. Interactive charts support hovering, zooming and series selection.</p>
</header>
<nav class="family-tabs" role="tablist" aria-label="Modelling frameworks">{nav}</nav>
<main>{''.join(sections)}</main>
<footer>Built from the latest saved model outputs and dissertation results. The page does not rerun estimation.</footer>
<script>
function resizeVisibleCharts() {{
  window.requestAnimationFrame(() => {{
    if (!window.Plotly) return;
    document.querySelectorAll('[role="tabpanel"]:not([hidden]) .plotly-graph-div')
      .forEach(chart => window.Plotly.Plots.resize(chart));
  }});
}}

function activateFamily(tab, updateHash = true) {{
  document.querySelectorAll('.family-tab').forEach(button => {{
    const selected = button === tab;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-selected', selected);
    document.getElementById(button.getAttribute('aria-controls')).hidden = !selected;
  }});
  if (updateHash) history.replaceState(null, '', `#${{tab.dataset.family}}`);
  resizeVisibleCharts();
}}

function activateCountry(tab) {{
  const familyPanel = tab.closest('.family-panel');
  familyPanel.querySelectorAll('.country-tab').forEach(button => {{
    const selected = button === tab;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-selected', selected);
    document.getElementById(button.getAttribute('aria-controls')).hidden = !selected;
  }});
  resizeVisibleCharts();
}}

function activateModel(tab) {{
  const familyPanel = tab.closest('.family-panel');
  familyPanel.querySelectorAll('.model-tab').forEach(button => {{
    const selected = button === tab;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-selected', selected);
    document.getElementById(button.getAttribute('aria-controls')).hidden = !selected;
  }});
  resizeVisibleCharts();
}}

function addTabKeys(selector, activate) {{
  const tabs = Array.from(document.querySelectorAll(selector));
  tabs.forEach(tab => {{
    tab.addEventListener('click', () => activate(tab));
    tab.addEventListener('keydown', event => {{
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const peers = Array.from(tab.parentElement.querySelectorAll(selector));
      let next = event.key === 'Home' ? 0 : event.key === 'End' ? peers.length - 1 : peers.indexOf(tab) + (event.key === 'ArrowRight' ? 1 : -1);
      next = (next + peers.length) % peers.length;
      peers[next].focus();
      activate(peers[next]);
    }});
  }});
}}

addTabKeys('.family-tab', activateFamily);
addTabKeys('.country-tab', activateCountry);
addTabKeys('.model-tab', activateModel);
const requestedFamily = window.location.hash.slice(1).toLowerCase();
const requestedTab = document.querySelector(`.family-tab[data-family="${{requestedFamily}}"]`);
if (requestedTab) activateFamily(requestedTab, false);

const modelTable = document.getElementById('all-models-table');
const modelSearch = document.getElementById('model-table-search');
if (modelTable && modelSearch) {{
  const tableBody = modelTable.querySelector('tbody');
  modelSearch.addEventListener('input', () => {{
    const query = modelSearch.value.trim().toLowerCase();
    tableBody.querySelectorAll('tr').forEach(row => {{
      row.hidden = !row.dataset.model.includes(query);
    }});
  }});
  modelTable.querySelectorAll('.table-sort').forEach((button, column) => {{
    let ascending = true;
    button.addEventListener('click', () => {{
      const rows = Array.from(tableBody.querySelectorAll('tr'));
      rows.sort((left, right) => {{
        const a = left.cells[column].dataset.value;
        const b = right.cells[column].dataset.value;
        const comparison = column === 0
          ? a.localeCompare(b)
          : Number(a) - Number(b);
        return ascending ? comparison : -comparison;
      }});
      rows.forEach(row => tableBody.appendChild(row));
      ascending = !ascending;
    }});
  }});
}}
resizeVisibleCharts();
</script>
<script>{(config.PORTFOLIO_ROOT / 'Charts/inflation_scenarios.js').read_text(encoding='utf-8')}</script>
</body>
</html>'''


def main():
    config.OUTPUT.write_text(build_page(), encoding="utf-8")
    print(config.OUTPUT)


if __name__ == "__main__":
    main()
