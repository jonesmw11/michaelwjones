# Configuration for the interactive macro-model results dashboard.

from pathlib import Path


PORTFOLIO_ROOT = Path(__file__).resolve().parent.parent
ROOT = PORTFOLIO_ROOT / "macro-work"
OUTPUT = PORTFOLIO_ROOT / "results_dashboard.html"

COLORS = {
    "green": "#0B6E4F",
    "green_light": "#5BAE95",
    "grey": "#9A9A9A",
    "orange": "#B5651D",
    "blue": "#2A6F97",
    "red": "#A6242B",
    "ink": "#1A1A1A",
    "note": "#5A5A5A",
    "grid": "#EFEFEF",
}

COUNTRY_ORDER = ["AU", "JP", "KR", "USA"]

COUNTRIES = {
    "AU": {
        "name": "Australia",
        "summary": "Quarterly inflation VAR forecasts are followed by the SMOG state-space estimates of the output gap and NAIRU.",
    },
    "JP": {
        "name": "Japan",
        "summary": "Monthly national and Tokyo CPI forecasts are followed by the Japanese SMOG estimates of spare capacity and the NAIRU.",
    },
    "KR": {
        "name": "South Korea",
        "summary": "Monthly CPI and PPI forecasts are followed by smoothed and filtered Korean SMOG estimates.",
    },
    "USA": {
        "name": "United States",
        "summary": "The MCT model extracts a persistent inflation trend from detailed PCE sectors and reports posterior uncertainty.",
    },
}

INFLATION_MODELS = {
    "AU": [
        {
            "title": "Australia: CPI inflation forecast",
            "path": ROOT / "AU/Inflation Model/results/au_inflation_forecast.csv",
            "frequency": "Q",
            "forecast_steps": 12,
            "description": "A quarterly VAR forecasts headline, trimmed-mean and ex-food-and-energy CPI using unemployment, expectations, import prices, oil and pipeline-price pressures.",
            "series": {
                "headline_yoy": "Headline",
                "trimmed_mean_yoy": "Trimmed mean",
                "ex_food_energy_yoy": "Ex food & energy",
            },
        },
    ],
    "JP": [
        {
            "title": "Japan: national CPI inflation forecast",
            "path": ROOT / "JP/Inflation Model/results/jp_cpi_inflation_forecast.csv",
            "frequency": "M",
            "forecast_steps": 36,
            "description": "A monthly VAR forecasts four national CPI measures using unemployment, oil, import prices and Stage 2 pipeline prices.",
            "series": {
                "headline_yoy": "Headline",
                "ex_fresh_food_yoy": "Ex fresh food",
                "ex_fresh_food_energy_yoy": "Ex fresh food & energy",
                "ex_food_energy_yoy": "Ex food & energy",
            },
        },
        {
            "title": "Japan: Tokyo CPI inflation forecast",
            "path": ROOT / "JP/Inflation Model/results/jp_tokyo_inflation_forecast.csv",
            "frequency": "M",
            "forecast_steps": 36,
            "description": "The Tokyo VAR uses the same monthly drivers to provide a timelier regional view of headline and core inflation.",
            "series": {
                "tokyo_headline_yoy": "Headline",
                "tokyo_ex_fresh_food_yoy": "Ex fresh food",
                "tokyo_ex_fresh_food_energy_yoy": "Ex fresh food & energy",
            },
        },
    ],
    "KR": [
        {
            "title": "South Korea: CPI inflation forecast",
            "path": ROOT / "KR/Inflation Model/results/kr_cpi_inflation_forecast.csv",
            "frequency": "M",
            "forecast_steps": 36,
            "description": "A monthly VAR forecasts headline and core CPI using inflation expectations, oil, import prices and unemployment.",
            "series": {"headline_yoy": "Headline", "core_yoy": "Core"},
        },
        {
            "title": "South Korea: PPI inflation forecast",
            "path": ROOT / "KR/Inflation Model/results/kr_ppi_inflation_forecast.csv",
            "frequency": "M",
            "forecast_steps": 36,
            "description": "A companion monthly VAR projects producer-price inflation from the same domestic and external cost drivers.",
            "series": {"ppi_yoy": "Producer prices"},
        },
    ],
    "USA": [],
}

SMOG_MODELS = {
    country: {
        "smoothed": ROOT / f"{country}/SMOG Model/results/smog_{country.lower()}_python.csv",
        "filtered": ROOT / f"{country}/SMOG Model/results/smog_{country.lower()}_filtered_states.csv",
        "inputs": ROOT / f"{country}/SMOG Model/code/{country} SMOG Model Inputs.xlsx",
        "description": description,
    }
    for country, description in {
        "AU": "The state-space model combines non-farm GDP, unemployment and inflation to estimate the output gap, potential output and NAIRU.",
        "JP": "The state-space model combines GDP, unemployment, core inflation, labour costs, import prices and Tankan expectations to estimate spare capacity and the NAIRU.",
        "KR": "The state-space model combines GDP, unemployment, core inflation and labour-cost growth, with import prices and Bank of Korea expectations, to estimate spare capacity and the NAIRU.",
    }.items()
}

MCT_MODEL = {
    "result": ROOT / "USA/Inflation Model/mct_model/results/python/current_reconstruction_d3000_b3000_t2_s2022_labelled.csv",
    "pce_prices": ROOT / "USA/Inflation Model/pce_official/monthly_prices.csv",
    "core_pce_line": "374",
    "results_workbook": ROOT / "USA/Inflation Model/mct_model/results/python/current_reconstruction_d3000_b3000_t2_s2022.xlsx",
    "sector_mapping": ROOT / "USA/Inflation Model/mct_model/data/sector_mapping.csv",
    "default_sector": "Housing excluding gas and electric utilities",
    "description": "A Bayesian dynamic-factor state-space model extracts persistent inflation from 17 detailed PCE sectors. Twelve-month Core PCE is shown for context but is not a model input; MCT combines the estimated trends of the 14 sectors retained in the core basket.",
    "sector_trends_description": "Each line is the model-estimated persistent trend for one of the 17 PCE sectors: its common-trend contribution plus its sector-specific trend. Dashed lines identify the three food and energy sectors estimated by the model but excluded when the final MCT aggregate is formed.",
    "target": 2.0,
}

MASTER_WORK = {
    "root": PORTFOLIO_ROOT / "masters-dissertation",
    "pdf": PORTFOLIO_ROOT / "masters-dissertation/Michael Jones MSc Statistical Science Dissertation Final.pdf",
    "figures": {
        "black_scholes": PORTFOLIO_ROOT / "masters-dissertation/figures/02-black-scholes-fitted-option-prices.png",
        "black_scholes_maturities": PORTFOLIO_ROOT / "masters-dissertation/figures/04-black-scholes-full-chain-vs-per-maturity-fitted-prices.png",
        "best_errors": PORTFOLIO_ROOT / "masters-dissertation/figures/11-best-fitting-models-pricing-errors.png",
        "best_volatility": PORTFOLIO_ROOT / "masters-dissertation/figures/14-best-fitting-models-implied-volatility.png",
    },
    "black_scholes": {
        "contracts": 212,
        "expiries": 7,
        "single_sigma": 0.6851,
        "single_ape": 12.43,
        "single_aae": 11.4802,
        "single_rmse": 12.3578,
        "single_arpe": 17.48,
        "per_maturity_rmse": 1.4710,
        "maturities": [0.038356, 0.115068, 0.191781, 0.287671, 0.364384, 0.460274, 0.613699],
        "labels": ["Aug 2026", "Sep 2026", "Oct 2026", "Nov 2026", "Dec 2026", "Jan 2027", "Mar 2027"],
        "sigmas": [0.8941, 0.7880, 0.7355, 0.7004, 0.6846, 0.6201, 0.5993],
    },
    "best_models": [
        "BNS Gamma–OU",
        "Meixner–Gamma–OU",
        "Meixner–IG–OU",
        "VG–Gamma–OU",
        "VG–IG–OU",
    ],
    "best_model_parameters": {
        "BNS Gamma–OU": {
            "family": "BNS", "clock": "Gamma-OU",
            "levy": [-210.7703], "time_change": [9.2976, 5.5663, 4226.0556, 0.65821],
        },
        "Meixner–Gamma–OU": {
            "family": "Meixner", "clock": "Gamma-OU",
            "levy": [0.140, -0.732, 82.520], "time_change": [8.412, 1.573, 7.984],
        },
        "Meixner–IG–OU": {
            "family": "Meixner", "clock": "IG-OU",
            "levy": [0.162, -0.606, 64.966], "time_change": [9.684, 2.169, 8.047],
        },
        "VG–Gamma–OU": {
            "family": "Variance Gamma", "clock": "Gamma-OU",
            "levy": [2273.296, 50.103, 542.433], "time_change": [7.504, 2.024, 59.556],
        },
        "VG–IG–OU": {
            "family": "Variance Gamma", "clock": "IG-OU",
            "levy": [1289.974, 39.722, 118.125], "time_change": [9.322, 28.730, 103.776],
        },
    },
    "levy_parameters": {
        "Meixner": [0.0013, -3.0425, 1350.91],
        "Variance Gamma": [1.0519e8, 9.2905e7, 1.4971e4],
        "CGMY": [2.9389148469902704, 60.042955900892906, 130.25953209277085, 1.3555548383378415],
        "NIG": [1.4232e5, 3.6011e4, 6.0471e4],
    },
    "model_results": {
        "BNS Gamma–OU": "k200_bns_calibration.csv",
        "BNS IG–OU": "k200_bns_ig_calibration.csv",
        "Meixner": "k200_meixner_calibration.csv",
        "Meixner–CIR": "k200_Meixner_CIR.csv",
        "Meixner–Gamma–OU": "k200_Meixner_Gamma-OU.csv",
        "Meixner–IG–OU": "k200_Meixner_IG-OU.csv",
        "Variance Gamma": "k200_vg_calibration.csv",
        "VG–CIR": "k200_VG_CIR.csv",
        "VG–Gamma–OU": "k200_VG_Gamma-OU.csv",
        "VG–IG–OU": "k200_VG_IG-OU.csv",
        "CGMY": "k200_cgmy_calibration.csv",
        "CGMY–CIR": "k200_CGMY_CIR.csv",
        "CGMY–Gamma–OU": "k200_CGMY_Gamma-OU.csv",
        "CGMY–IG–OU": "k200_CGMY_IG-OU.csv",
        "NIG": "k200_nig_calibration.csv",
        "NIG–CIR": "k200_NIG_CIR.csv",
        "NIG–Gamma–OU": "k200_NIG_Gamma-OU.csv",
        "NIG–IG–OU": "k200_NIG_IG-OU.csv",
        "GH": "k200_gh_calibration.csv",
    },
}
