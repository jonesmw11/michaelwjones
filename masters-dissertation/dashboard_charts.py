# Interactive charts built from the dissertation's saved option chain and calibrations.

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative
from scipy.special import gamma as gamma_fn, gammaln, loggamma
from scipy.stats import norm


ROOT = Path(__file__).resolve().parent
CHAIN_PATH = ROOT / "code/KOSPI 200 option data.csv"
RESULTS = ROOT / "results"


def load_chain():
    chain = pd.read_csv(CHAIN_PATH, parse_dates=["expiry_date", "snapshot_date"])
    chain["expiry_label"] = chain["expiry_date"].dt.strftime("%b %Y")
    forward = chain["spot_price"] * np.exp((chain["rate"] - chain["div_yld"]) * chain["ttm"])
    chain["log_m"] = np.log(chain["strike"] / forward)
    return chain


def black_scholes_call(strike, maturity, rate, dividend, sigma, spot):
    strike = np.asarray(strike, dtype=float)
    maturity = np.asarray(maturity, dtype=float)
    rate = np.asarray(rate, dtype=float)
    dividend = np.asarray(dividend, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    root_t = np.sqrt(maturity)
    d1 = (np.log(spot / strike) + (rate - dividend + 0.5 * sigma ** 2) * maturity) / (sigma * root_t)
    d2 = d1 - sigma * root_t
    return spot * np.exp(-dividend * maturity) * norm.cdf(d1) - strike * np.exp(-rate * maturity) * norm.cdf(d2)


def style_figure(fig, colors, xlabel, ylabel, height=540):
    fig.update_layout(
        height=height,
        margin=dict(l=72, r=28, t=72, b=65),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(
            family="Gill Sans MT, Gill Sans, Arial, sans-serif",
            size=14,
            color=colors["ink"],
        ),
        hovermode="closest",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, bgcolor="rgba(255,255,255,0)",
        ),
        xaxis=dict(
            title=xlabel, showgrid=False, showline=True,
            linecolor="#C8C8C8", zeroline=False,
        ),
        yaxis=dict(
            title=ylabel, gridcolor="#EFEFEF", zeroline=False,
        ),
    )
    return fig


def add_expiry_dropdown(fig, labels, traces_per_expiry):
    total = len(fig.data)
    buttons = []
    for number, label in enumerate(labels):
        visible = [False] * total
        start = number * traces_per_expiry
        visible[start:start + traces_per_expiry] = [True] * traces_per_expiry
        buttons.append(dict(
            label=label,
            method="update",
            args=[
                {"visible": visible},
                {"xaxis.autorange": True, "yaxis.autorange": True},
            ],
        ))
    fig.update_layout(
        updatemenus=[dict(
            buttons=buttons,
            direction="down",
            showactive=True,
            x=0.02,
            xanchor="left",
            y=1.35,
            yanchor="top",
            bgcolor="white",
            bordercolor="#D5D5D5",
            borderwidth=1,
        )],
        annotations=[dict(
            text="Expiry",
            x=0.02,
            xref="paper",
            xanchor="left",
            y=1.47,
            yref="paper",
            yanchor="top",
            showarrow=False,
        )],
        margin=dict(l=72, r=28, t=180, b=65),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0)",
            borderwidth=0,
        ),
    )
    return fig


def model_prices(filename, chain):
    result = pd.read_csv(RESULTS / filename)
    return result.set_index("conId")["model_price"].reindex(chain["conId"]).to_numpy()


def all_model_metrics(work):
    chain = load_chain()
    spot = float(chain["spot_price"].iloc[0])
    black_scholes = black_scholes_call(
        chain["strike"], chain["ttm"], chain["rate"], chain["div_yld"],
        work["black_scholes"]["single_sigma"], spot,
    )
    model_order = [
        "Black–Scholes", "Meixner", "Variance Gamma", "CGMY", "NIG", "GH",
        "BNS Gamma–OU", "BNS IG–OU",
        "Meixner–CIR", "Meixner–Gamma–OU", "Meixner–IG–OU",
        "VG–CIR", "VG–Gamma–OU", "VG–IG–OU",
        "CGMY–CIR", "CGMY–Gamma–OU", "CGMY–IG–OU",
        "NIG–CIR", "NIG–Gamma–OU", "NIG–IG–OU",
    ]
    price_series = {"Black–Scholes": black_scholes}
    price_series.update({
        name: model_prices(work["model_results"][name], chain)
        for name in model_order[1:]
    })
    best = set(work["best_models"])
    rows = []
    for name in model_order:
        absolute_error = np.abs(chain["mid"].to_numpy() - price_series[name])
        metrics = {
            "model": name,
            "ape": 100 * absolute_error.mean() / chain["mid"].mean(),
            "aae": absolute_error.mean(),
            "rmse": np.sqrt(np.mean(absolute_error ** 2)),
            "arpe": 100 * np.mean(absolute_error / chain["mid"].to_numpy()),
            "best": name in best,
        }
        if name == "Black–Scholes":
            metrics.update({
                "ape": work["black_scholes"]["single_ape"],
                "aae": work["black_scholes"]["single_aae"],
                "rmse": work["black_scholes"]["single_rmse"],
                "arpe": work["black_scholes"]["single_arpe"],
            })
        rows.append(metrics)
    return rows


def chart_palette(colors):
    return [
        colors["green"], colors["orange"], colors["blue"], colors["red"],
        *qualitative.Safe,
    ]


def option_data_figure(colors):
    chain = load_chain()
    labels = chain.sort_values("ttm")["expiry_label"].drop_duplicates().tolist()
    palette = chart_palette(colors)
    fig = go.Figure()
    for number, label in enumerate(labels):
        subset = chain.loc[chain["expiry_label"] == label].sort_values("strike")
        fig.add_trace(go.Scatter(
            x=subset["strike"],
            y=subset["mid"],
            mode="lines+markers",
            name=label,
            line=dict(color=palette[number], width=1.5),
            marker=dict(color=palette[number], size=7),
            customdata=subset[["ttm", "iv"]],
            hovertemplate=f"{label}<br>Strike: %{{x:.1f}}<br>Market price: %{{y:.3f}}<br>Maturity: %{{customdata[0]:.3f}} years<br>Market IV: %{{customdata[1]:.2%}}<extra></extra>",
        ))
    return style_figure(fig, colors, "Strike", "Market option price")


def full_chain_fitted_values_figure(series, colors):
    chain = load_chain()
    palette = chart_palette(colors)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chain["strike"], y=chain["mid"], mode="markers", name="Market",
        marker=dict(
            color="white", line=dict(color=colors["ink"], width=1.6),
            size=8, symbol="circle",
        ),
        customdata=chain[["expiry_label", "ttm"]],
        hovertemplate="Market<br>Strike: %{x:.1f}<br>Price: %{y:.3f}<br>Expiry: %{customdata[0]}<br>Maturity: %{customdata[1]:.3f} years<extra></extra>",
    ))
    for number, (name, values) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=chain["strike"], y=values, mode="markers", name=name,
            marker=dict(color=palette[number], size=7, symbol="x"),
            customdata=chain[["expiry_label", "ttm"]],
            hovertemplate=f"{name}<br>Strike: %{{x:.1f}}<br>Fitted price: %{{y:.3f}}<br>Expiry: %{{customdata[0]}}<br>Maturity: %{{customdata[1]:.3f}} years<extra></extra>",
        ))
    return style_figure(fig, colors, "Strike", "Option price")


def black_scholes_fitted_figures(work, colors):
    chain = load_chain()
    bs = work["black_scholes"]
    spot = float(chain["spot_price"].iloc[0])
    single = black_scholes_call(
        chain["strike"], chain["ttm"], chain["rate"], chain["div_yld"],
        bs["single_sigma"], spot,
    )
    sigma_by_maturity = {
        round(maturity, 6): sigma
        for maturity, sigma in zip(bs["maturities"], bs["sigmas"])
    }
    expiry_sigma = chain["ttm"].round(6).map(sigma_by_maturity).to_numpy()
    separate = black_scholes_call(
        chain["strike"], chain["ttm"], chain["rate"], chain["div_yld"],
        expiry_sigma, spot,
    )
    return (
        full_chain_fitted_values_figure({"Black–Scholes, one volatility": single}, colors),
        full_chain_fitted_values_figure({"Black–Scholes, fitted by expiry": separate}, colors),
    )


def black_scholes_term_structure_figure(work, colors):
    bs = work["black_scholes"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=bs["maturities"],
        y=bs["sigmas"],
        mode="lines+markers+text",
        name="Separate fit for each expiry",
        text=bs["labels"],
        textposition="top center",
        line=dict(color=colors["green"], width=2.7),
        marker=dict(size=8),
        hovertemplate="%{text}<br>Maturity: %{x:.3f} years<br>Volatility: %{y:.1%}<extra></extra>",
    ))
    fig.add_hline(
        y=bs["single_sigma"],
        line_color=colors["orange"], line_dash="dash", line_width=1.7,
        annotation_text=f'Single full-chain volatility: {bs["single_sigma"]:.1%}',
        annotation_position="bottom right",
    )
    return style_figure(fig, colors, "Time to expiry, years", "Annualized volatility")


def market_implied_volatility_figure(colors):
    chain = load_chain()
    labels = chain.sort_values("ttm")["expiry_label"].drop_duplicates().tolist()
    fig = go.Figure()
    palette = chart_palette(colors)
    for number, label in enumerate(labels):
        subset = chain.loc[chain["expiry_label"] == label].sort_values("strike")
        fig.add_trace(go.Scatter(
            x=subset["strike"],
            y=subset["iv"],
            mode="lines+markers",
            name=label,
            line=dict(color=palette[number], width=2.0),
            marker=dict(size=6),
            hovertemplate="Strike: %{x:.1f}<br>Implied volatility: %{y:.2%}<extra></extra>",
        ))
    fig = style_figure(fig, colors, "Strike", "Black–Scholes implied volatility")
    fig.update_yaxes(tickformat=".0%")
    return fig


def levy_fitted_values_figure(work, colors):
    chain = load_chain()
    names = ["Meixner", "Variance Gamma", "CGMY", "NIG", "GH"]
    series = {
        name: model_prices(work["model_results"][name], chain)
        for name in names
    }
    return full_chain_fitted_values_figure(series, colors)


def psi_vg(u, c, g, m):
    return -c * np.log1p(((m - g) * 1j * u + u ** 2) / (g * m))


def psi_meixner(u, alpha, beta, delta):
    return 2 * delta * (
        np.log(np.cos(beta / 2))
        - np.log(np.cosh((alpha * u - 1j * beta) / 2))
    )


def psi_cgmy(u, c, g, m, y):
    return c * gamma_fn(-y) * ((m - 1j * u) ** y - m ** y + (g + 1j * u) ** y - g ** y)


def psi_nig(u, alpha, beta, delta):
    return -delta * (np.sqrt(alpha ** 2 - (beta + 1j * u) ** 2) - np.sqrt(alpha ** 2 - beta ** 2))


def varphi_gamma_ou(u, maturity, lam, a, b):
    u = np.asarray(u, dtype=complex)
    decay = 1 - np.exp(-lam * maturity)
    term1 = 1j * u * decay / lam
    term2 = lam * a / (1j * u - lam * b) * (
        b * np.log(b / (b - 1j * u * decay / lam)) - 1j * u * maturity
    )
    return np.exp(term1 + term2)


def varphi_ig_ou(u, maturity, lam, a, b):
    u = np.asarray(u, dtype=complex)
    kap = -2 * b ** -2 * 1j * u / lam
    decay = 1 - np.exp(-lam * maturity)
    root = np.sqrt(1 + kap * decay)
    adjustment = (1 - root) / kap + (1 / np.sqrt(1 + kap)) * (
        np.arctanh(root / np.sqrt(1 + kap))
        - np.arctanh(1 / np.sqrt(1 + kap))
    )
    return np.exp(
        1j * u * decay / lam
        + 2 * a * 1j * u / (b * lam) * adjustment
    )


def stochastic_time_characteristic(u, maturity, rate, dividend, family, levy, clock, time_change):
    exponents = {
        "Meixner": psi_meixner,
        "Variance Gamma": psi_vg,
    }
    clocks = {
        "Gamma-OU": varphi_gamma_ou,
        "IG-OU": varphi_ig_ou,
    }
    exponent = exponents[family]
    transform = clocks[clock]
    numerator = transform(-1j * exponent(u, *levy), maturity, *time_change)
    denominator = transform(-1j * exponent(-1j, *levy), maturity, *time_change)
    return np.exp(1j * u * (rate - dividend) * maturity) * numerator / denominator ** (1j * u)


def bns_gamma_characteristic(u, maturity, rate, dividend, rho, lam, a, b, sigma0_sq):
    u = np.asarray(u, dtype=complex)
    f1 = 1j * u * rho - 0.5 * (u ** 2 + 1j * u) * (1 - np.exp(-lam * maturity))
    f2 = 1j * u * rho - 0.5 * (u ** 2 + 1j * u)
    term1 = 1j * u * (rate - dividend - a * lam * rho / (b - rho)) * maturity
    term2 = -0.5 * (u ** 2 + 1j * u) * (1 - np.exp(-lam * maturity)) / lam * sigma0_sq
    term3 = a / (b - f2) * (
        b * np.log((b - f1) / (b - 1j * u * rho))
        + f2 * lam * maturity
    )
    return np.exp(term1 + term2 + term3)


def meixner_density(x, alpha, beta, delta, location):
    z = (x - location) / alpha
    log_constant = (
        2 * delta * np.log(2 * np.cos(beta / 2))
        - np.log(2 * alpha * np.pi)
        - gammaln(2 * delta)
    )
    return np.exp(np.clip(
        log_constant + beta * z + 2 * np.real(loggamma(delta + 1j * z)),
        -745,
        700,
    ))


def levy_drift(name, parameters, rate, dividend):
    if name == "Meixner":
        alpha, beta, delta = parameters
        return rate - dividend - 2 * delta * (
            np.log(np.cos(beta / 2)) - np.log(np.cos((alpha + beta) / 2))
        )
    if name == "Variance Gamma":
        c, g, m = parameters
        return rate - dividend + c * np.log1p((m - g - 1) / (m * g))
    if name == "CGMY":
        c, g, m, y = parameters
        return rate - dividend - c * gamma_fn(-y) * (
            (m - 1) ** y - m ** y + (g + 1) ** y - g ** y
        )
    if name == "NIG":
        alpha, beta, delta = parameters
        return rate - dividend + delta * (
            np.sqrt(alpha ** 2 - (beta + 1) ** 2)
            - np.sqrt(alpha ** 2 - beta ** 2)
        )
    raise ValueError(name)


def fourier_density(x, maturity, exponent, parameters, drift, sigma):
    frequency = np.linspace(0, 60 / (sigma * np.sqrt(maturity)), 4096)
    characteristic = np.exp(
        maturity * exponent(frequency, *parameters)
        + 1j * frequency * drift * maturity
    )
    density = np.empty_like(x)
    for start in range(0, len(x), 100):
        stop = min(start + 100, len(x))
        integrand = np.real(
            np.exp(-1j * x[start:stop, None] * frequency[None, :])
            * characteristic[None, :]
        )
        density[start:stop] = np.trapezoid(integrand, frequency, axis=1) / np.pi
    density = np.clip(density, 0, None)
    mass = np.trapezoid(density, x)
    return density / mass if mass > 0 else density


def levy_density_figure(work, colors):
    chain = load_chain()
    maturities = chain.sort_values("ttm")["ttm"].drop_duplicates().tolist()
    labels = [
        chain.loc[chain["ttm"] == maturity, "expiry_label"].iloc[0]
        for maturity in maturities
    ]
    sigma = work["black_scholes"]["single_sigma"]
    exponents = {
        "Variance Gamma": psi_vg,
        "CGMY": psi_cgmy,
        "NIG": psi_nig,
    }
    series_names = ["Black–Scholes normal", "Meixner", "Variance Gamma", "CGMY", "NIG"]
    palette = [colors["grey"], colors["green"], colors["orange"], colors["blue"], colors["red"]]
    fig = go.Figure()
    for maturity_number, (maturity, label) in enumerate(zip(maturities, labels)):
        row = chain.loc[chain["ttm"] == maturity].iloc[0]
        rate, dividend = float(row["rate"]), float(row["div_yld"])
        centre = (rate - dividend - 0.5 * sigma ** 2) * maturity
        width = 5 * sigma * np.sqrt(maturity)
        x = np.linspace(centre - width, centre + width, 500)
        normal_density = norm.pdf(x, loc=centre, scale=sigma * np.sqrt(maturity))
        densities = {"Black–Scholes normal": normal_density}
        for name in series_names[1:]:
            parameters = tuple(work["levy_parameters"][name])
            drift = levy_drift(name, parameters, rate, dividend)
            if name == "Meixner":
                alpha, beta, delta = parameters
                density = meixner_density(x, alpha, beta, delta * maturity, drift * maturity)
                density = density / np.trapezoid(density, x)
            else:
                density = fourier_density(
                    x, maturity, exponents[name], parameters, drift, sigma,
                )
            densities[name] = density
        for series_number, name in enumerate(series_names):
            fig.add_trace(go.Scatter(
                x=x,
                y=densities[name],
                mode="lines",
                name=name,
                visible=maturity_number == 0,
                line=dict(color=palette[series_number], width=2.4),
                hovertemplate=f"{name}<br>Log return: %{{x:.3f}}<br>Density: %{{y:.3f}}<extra></extra>",
            ))
    fig = style_figure(fig, colors, "Log return", "Risk-neutral density")
    return add_expiry_dropdown(fig, labels, len(series_names))


def best_model_fitted_values_figure(work, colors):
    chain = load_chain()
    series = {
        name: model_prices(work["model_results"][name], chain)
        for name in work["best_models"]
    }
    return full_chain_fitted_values_figure(series, colors)


def best_model_pricing_errors_figure(work, colors):
    chain = load_chain()
    labels = chain.sort_values("ttm")["expiry_label"].drop_duplicates().tolist()
    palette = [colors["green"], colors["orange"], colors["blue"], colors["red"], qualitative.Safe[4]]
    errors = {}
    for name in work["best_models"]:
        result = pd.read_csv(RESULTS / work["model_results"][name])
        errors[name] = result.set_index("conId")["error"].reindex(chain["conId"]).to_numpy()
    fig = go.Figure()
    for expiry_number, label in enumerate(labels):
        subset = chain.loc[chain["expiry_label"] == label].sort_values("log_m")
        for model_number, name in enumerate(work["best_models"]):
            values = pd.Series(errors[name], index=chain.index).loc[subset.index]
            fig.add_trace(go.Scatter(
                x=subset["log_m"],
                y=values,
                mode="markers",
                name=name,
                visible=expiry_number == 0,
                marker=dict(color=palette[model_number], size=7),
                hovertemplate=f"{name}<br>Log-moneyness: %{{x:.3f}}<br>Pricing error: %{{y:.3f}}<extra></extra>",
            ))
    fig.add_hline(y=0, line_color=colors["grey"], line_dash="dot", line_width=1)
    fig = style_figure(fig, colors, "Forward log-moneyness", "Model price − market price")
    return add_expiry_dropdown(fig, labels, len(work["best_models"]))


def characteristic_density(x, characteristic, frequency_max):
    frequency = np.linspace(1e-10, frequency_max, 4096)
    values = characteristic(frequency)
    density = np.empty_like(x)
    for start in range(0, len(x), 100):
        stop = min(start + 100, len(x))
        integrand = np.real(
            np.exp(-1j * x[start:stop, None] * frequency[None, :])
            * values[None, :]
        )
        density[start:stop] = np.trapezoid(integrand, frequency, axis=1) / np.pi
    density = np.clip(density, 0, None)
    mass = np.trapezoid(density, x)
    return density / mass if mass > 0 else density


def best_model_density_figure(work, colors):
    chain = load_chain()
    maturities = chain.sort_values("ttm")["ttm"].drop_duplicates().tolist()
    labels = [
        chain.loc[chain["ttm"] == maturity, "expiry_label"].iloc[0]
        for maturity in maturities
    ]
    parameters = work["best_model_parameters"]
    model_order = work["best_models"]
    palette = [
        colors["grey"], colors["green"], colors["orange"],
        colors["blue"], colors["red"], qualitative.Safe[4],
    ]
    single_sigma = work["black_scholes"]["single_sigma"]
    fig = go.Figure()
    for maturity_number, (maturity, label) in enumerate(zip(maturities, labels)):
        row = chain.loc[chain["ttm"] == maturity].iloc[0]
        rate, dividend = float(row["rate"]), float(row["div_yld"])
        centre = (rate - dividend - 0.5 * single_sigma ** 2) * maturity
        root_t = np.sqrt(maturity)
        width = 5 * single_sigma * root_t
        x = np.linspace(centre - width, centre + width, 500)
        densities = {
            "Black–Scholes normal": norm.pdf(
                x, loc=centre, scale=single_sigma * root_t,
            )
        }
        for name in model_order:
            spec = parameters[name]
            if spec["family"] == "BNS":
                rho = spec["levy"][0]
                lam, a, b, sigma0_sq = spec["time_change"]
                characteristic = lambda u, rho=rho, lam=lam, a=a, b=b, sigma0_sq=sigma0_sq: bns_gamma_characteristic(
                    u, maturity, rate, dividend, rho, lam, a, b, sigma0_sq,
                )
            else:
                characteristic = lambda u, spec=spec: stochastic_time_characteristic(
                    u, maturity, rate, dividend, spec["family"], spec["levy"],
                    spec["clock"], spec["time_change"],
                )
            densities[name] = characteristic_density(
                x, characteristic, 70 / (single_sigma * root_t),
            )
        for series_number, (name, density) in enumerate(densities.items()):
            fig.add_trace(go.Scatter(
                x=x, y=density, mode="lines", name=name,
                visible=maturity_number == 0,
                line=dict(color=palette[series_number], width=2.4),
                hovertemplate=f"{name}<br>Log return: %{{x:.3f}}<br>Density: %{{y:.3f}}<extra></extra>",
            ))
    fig = style_figure(fig, colors, "Log return", "Risk-neutral density")
    fig.update_xaxes(title="Log return over [0, T]")
    return add_expiry_dropdown(fig, labels, 1 + len(model_order))


def levy_unit_moments(family, parameters):
    if family == "Meixner":
        alpha, beta, delta = parameters
        mean = alpha * delta * np.tan(beta / 2)
        variance = alpha ** 2 * delta / (2 * np.cos(beta / 2) ** 2)
        return mean, variance
    if family == "Variance Gamma":
        c, g, m = parameters
        mean = c * (g - m) / (m * g)
        variance = c * (g ** 2 + m ** 2) / (m * g) ** 2
        return mean, variance
    raise ValueError(family)


def integrated_ou_variance(maturity, mean, variance, clock, time_change):
    lam, a, b = time_change
    epsilon = (1 - np.exp(-lam * maturity)) / lam
    psi = maturity - epsilon - 0.5 * lam * epsilon ** 2
    power = 2 if clock == "Gamma-OU" else 3
    return (
        variance * (epsilon + (a / b) * (maturity - epsilon))
        + mean ** 2 * (2 * a / (lam * b ** power)) * psi
    )


def bns_gamma_variance(maturity, rho, lam, a, b, sigma0_sq):
    epsilon = (1 - np.exp(-lam * maturity)) / lam
    return (
        sigma0_sq * epsilon
        + (lam * a / b) * (maturity - epsilon)
        + rho ** 2 * lam * (2 * a / b ** 2) * maturity
    )


def best_model_implied_volatility_figure(work, colors):
    parameters = work["best_model_parameters"]
    maturities = np.linspace(0.001, 0.70, 180)
    model_order = [
        "BNS Gamma–OU", "VG–Gamma–OU", "Meixner–IG–OU",
        "VG–IG–OU", "Meixner–Gamma–OU",
    ]
    palette = [colors["orange"], colors["blue"], colors["green"], "#CC79A7", "#E69F00"]
    fig = go.Figure()
    for model_number, name in enumerate(model_order):
        spec = parameters[name]
        if spec["family"] == "BNS":
            rho = spec["levy"][0]
            lam, a, b, sigma0_sq = spec["time_change"]
            variance = bns_gamma_variance(
                maturities, rho, lam, a, b, sigma0_sq,
            )
        else:
            mean, unit_variance = levy_unit_moments(spec["family"], spec["levy"])
            variance = integrated_ou_variance(
                maturities, mean, unit_variance,
                spec["clock"], spec["time_change"],
            )
        volatility = np.sqrt(variance / maturities)
        result = pd.read_csv(RESULTS / work["model_results"][name])
        rmse = np.sqrt(np.mean(result["error"] ** 2))
        fig.add_trace(go.Scatter(
            x=maturities,
            y=volatility,
            mode="lines",
            name=f"{name} (RMSE {rmse:.3f})",
            line=dict(color=palette[model_number], width=2.2),
            hovertemplate=f"{name}<br>Maturity: %{{x:.3f}} years<br>Annualized volatility: %{{y:.2%}}<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=work["black_scholes"]["maturities"],
        y=work["black_scholes"]["sigmas"],
        mode="markers",
        name="Black–Scholes, fitted per maturity",
        marker=dict(color="white", line=dict(color=colors["ink"], width=1.8), size=9),
        text=work["black_scholes"]["labels"],
        hovertemplate="%{text}<br>Fitted volatility: %{y:.2%}<extra></extra>",
    ))
    fig = style_figure(fig, colors, "Time to expiry, years", "Median Black–Scholes implied volatility")
    fig.add_hline(
        y=work["black_scholes"]["single_sigma"],
        line_color=colors["grey"], line_dash="dash", line_width=1.3,
        annotation_text="Single Black–Scholes volatility",
        annotation_position="bottom right",
    )
    fig.update_yaxes(title="Annualized volatility")
    fig.update_xaxes(range=[0, 0.70])
    fig.update_yaxes(tickformat=".0%", range=[0.58, 0.98])
    return fig


def build_master_figures(work, colors):
    black_scholes, black_scholes_by_expiry = black_scholes_fitted_figures(work, colors)
    return {
        "option_data": option_data_figure(colors),
        "black_scholes_fitted": black_scholes,
        "black_scholes_by_expiry": black_scholes_by_expiry,
        "black_scholes_term_structure": black_scholes_term_structure_figure(work, colors),
        "market_implied_volatility": market_implied_volatility_figure(colors),
        "levy_fitted": levy_fitted_values_figure(work, colors),
        "levy_densities": levy_density_figure(work, colors),
        "best_fitted": best_model_fitted_values_figure(work, colors),
        "best_errors": best_model_pricing_errors_figure(work, colors),
        "best_densities": best_model_density_figure(work, colors),
        "best_implied_volatility": best_model_implied_volatility_figure(work, colors),
    }
