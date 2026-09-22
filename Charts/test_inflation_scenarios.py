# Numerical integration checks against statsmodels, using all dashboard VARs.
# =============================================================================
#%% Imports and fixtures
import json
from pathlib import Path
import subprocess
import unittest

import numpy as np
from statsmodels.tsa.vector_ar.var_model import forecast

import results_dashboard_config as config
from inflation_scenarios import scenario_payload


# =============================================================================
#%% Run the exact browser engine with Node
def browser_projection(model, path):
    script = "const fs=require('fs'); const {projectOilScenario}=require('./inflation_scenarios.js'); const x=JSON.parse(fs.readFileSync(0,'utf8')); console.log(JSON.stringify(projectOilScenario(x.model,x.path)));"
    output = subprocess.run(["node", "-e", script], input=json.dumps(dict(model=model, path=path)),
                            capture_output=True, text=True, check=True, cwd=Path(__file__).parent)
    return json.loads(output.stdout)


# =============================================================================
#%% Baseline identity, oil intervention timing, and full recursive propagation
class OilScenarioTests(unittest.TestCase):
    def test_shared_edits_update_every_measure_and_reset(self):
        models = scenario_payload("AU", config.INFLATION_MODELS["AU"][0])
        edits = [[models[0]["dates"][2], 60], [models[0]["dates"][3], 55]]
        script = "const fs=require('fs'); const {projectCountryScenario}=require('./inflation_scenarios.js'); const x=JSON.parse(fs.readFileSync(0,'utf8')); console.log(JSON.stringify({changed:projectCountryScenario(x.models,new Map(x.edits)),reset:projectCountryScenario(x.models,new Map())}));"
        output = subprocess.run(["node", "-e", script], input=json.dumps(dict(models=models, edits=edits)),
                                capture_output=True, text=True, check=True, cwd=Path(__file__).parent)
        results = json.loads(output.stdout)
        for i, model in enumerate(models):
            rates = np.array(results["changed"][i]["rates"])
            oil = model["oilLast"] * np.cumprod(1 + rates[:, model["oilIndex"]] / 100)
            np.testing.assert_allclose(oil[2:4], [60, 55], atol=1e-9)
            np.testing.assert_allclose(results["reset"][i]["yoy"], model["baselineYoy"], atol=1e-9)
            self.assertGreater(np.max(np.abs(np.array(results["changed"][i]["yoy"]) - model["baselineYoy"])), 1e-5)

    def test_all_models(self):
        for country, specs in config.INFLATION_MODELS.items():
            for spec in specs:
                for model in scenario_payload(country, spec):
                    with self.subTest(country=country, title=spec["title"], measure=model["label"]):
                        baseline = browser_projection(model, model["oilBaseline"])
                        np.testing.assert_allclose(baseline["yoy"], model["baselineYoy"], atol=1e-9)
                        np.testing.assert_allclose(baseline["rates"], model["baseline"], atol=1e-9)
                        path = np.array(model["oilBaseline"])
                        path[2:8] *= 1.25
                        changed = browser_projection(model, path.tolist())
                        rows = np.array(model["seed"])
                        previous = model["oilLast"]
                        reference = []
                        for price in path:
                            row = forecast(rows, np.array(model["coefficients"]), np.array(model["intercept"]), 1)[0]
                            row[model["oilIndex"]] = 100 * (price / previous - 1)
                            previous = price
                            rows = np.vstack([rows, row])
                            reference.append(row)
                        np.testing.assert_allclose(changed["rates"], reference, atol=1e-9)
                        np.testing.assert_allclose(changed["yoy"][:3], baseline["yoy"][:3], atol=1e-9)
                        self.assertGreater(np.max(np.abs(np.array(changed["yoy"]) - baseline["yoy"])), 1e-5)
                        levels = np.r_[model["cpiHistory"], model["cpiHistory"][-1] * np.cumprod(1 + np.array(reference)[:, 0] / 100)]
                        year = model["year"]
                        np.testing.assert_allclose(changed["yoy"], 100 * (levels[year:] / levels[:-year] - 1), atol=1e-9)

    def test_zero_lag_and_invalid_price(self):
        model = dict(seed=[[1, 2]], coefficients=[], intercept=[1, 2], cpiHistory=[100], year=1, oilLast=50, oilIndex=1)
        np.testing.assert_allclose(browser_projection(model, [50, 60])["yoy"], [1, 1])
        with self.assertRaises(subprocess.CalledProcessError):
            browser_projection(model, [0])


# =============================================================================
#%% Direct execution
if __name__ == "__main__":
    unittest.main()
