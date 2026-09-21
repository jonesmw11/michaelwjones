# Validate package-backed state smoothing against the official implementation.
#
# MCT PIPELINE MAP
# [1] Source data -> prepare_inputs.py -> data/*.mat
# [2] Python entry -> run_pipeline.py -> run_python.py
# [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
# [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
# [5] Validation -> validate_python.py
# Optional Octave reference:
# prepare_runtime.py -> run_octave_pipeline.py -> run_mct.m -> export_results.py
#
# THIS FILE: STAGE 5, IMPLEMENTATION VALIDATION.
# It checks reproducibility, refreshed pseudo-observations, matrix assembly, and
# conditional Gaussian smoother calculations; it does not establish MCMC convergence.

# %% Numerical runtime configuration
# Limit numerical-library threading before importing NumPy and SciPy.
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')

# %% Imports and project path
# Load command-line, subprocess, numerical, MAT-file, and MCT implementation tools.
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy.io import loadmat, savemat
from mct_python import MCT, GaussianStates

ROOT = Path(__file__).resolve().parent


# %% Build one state-smoother validation fixture
# Save a state-space system, compare a zero-disturbance simulation-smoother result
# with the package's conditional smoothed mean, and retain the Python reference.
def make_fixture(states, name):
    m = states.model
    fixture = {'Y':m.endog,'SSM':{'H':m.design,'F':m.transition,'G':m.selection,
               'Sigma_eta':m.state_cov,'Sigma_eps':m.obs_cov,'mu_1':m.initialization.constant[:,None],
               'Sigma_1':m.initialization.stationary_cov}}
    folder = ROOT/'results/validation'
    folder.mkdir(exist_ok=True,parents=True)
    savemat(folder/f'{name}_input.mat',fixture)
    expected = m.smooth().smoothed_state.T
    sampler = states.sampler
    sampler.simulate(measurement_disturbance_variates=np.zeros(m.nobs*m.k_endog),
                     state_disturbance_variates=np.zeros(m.nobs*m.k_posdef),
                     initial_state_variates=np.zeros(m.k_states))
    np.testing.assert_allclose(sampler.simulated_state.T,expected,atol=1e-9)
    savemat(folder/f'{name}_python.mat',{'states':expected})


# %% Run Python and optional upstream comparisons
# Exercise the main, loading, and volatility smoothers; test refreshed data and
# seeded reproducibility; optionally compare matrices and smoother means with Octave.
def validate(octave=None):
    data = loadmat(ROOT/'data/replication_202310.mat',simplify_cells=True)
    y = data['y'][-36:,:3]
    model = MCT(y,seed=87)
    make_fixture(model.states,'initial')
    model.step()
    make_fixture(model.states,'latent')
    make_fixture(model.loadings,'loadings')
    make_fixture(model.vol_specific.states,'volatility')
    # Check that rebinding data updates a previously created simulation smoother.
    g = GaussianStates(np.zeros((5,1)),np.ones((1,1)),np.ones((1,1)),np.ones((1,1)))
    g.configure(np.ones((1,1)),np.array([[.1]]),np.array([[.2]]))
    g.draw(np.random.default_rng(1))
    g.configure(np.ones((1,1)),np.array([[.1]]),np.array([[.2]]),np.full((5,1),10.))
    g.draw(np.random.default_rng(2))
    sim = g.sampler
    sim.simulate(measurement_disturbance_variates=np.zeros(5),state_disturbance_variates=np.zeros(5),initial_state_variates=np.zeros(1))
    np.testing.assert_allclose(sim.simulated_state,g.model.smooth().smoothed_state,atol=1e-10)
    fresh = GaussianStates(np.full((5,1),10.),np.ones((1,1)),np.ones((1,1)),np.ones((1,1)))
    fresh.configure(np.ones((1,1)),np.array([[.1]]),np.array([[.2]]))
    np.testing.assert_allclose(sim.simulated_state,fresh.model.smooth().smoothed_state,atol=1e-10)
    duplicate = MCT(y,seed=87)
    duplicate.step()
    np.testing.assert_array_equal(model.tau_i,duplicate.tau_i)
    report = {'same_seed_reproducibility':'PASS','updated_data_smoother':'PASS','official_smoother_comparisons':{}}
    if octave:
        source = (ROOT/'upstream/functions/estimate_MCT.m').read_text()
        source = source.split('% Initialize state variables')[0]
        source = source.replace('function output = estimate_MCT_new(y, prior, settings, initial)','function output = reference_matrices(y, prior, settings)',1)
        source += '\noutput.SSM=SSM; output.SSM_TVC=SSM_TVC;\nend\n'
        (ROOT/'results/validation/reference_matrices.m').write_text(source)
        p = model.priors
        prior = {'prec_MA':p.prec_ma,'nu_lam':p.nu_lam,'s2_lam':p.s2_lam,'nu_gam':p.nu_gam,'s2_gam':p.s2_gam,'a_ps':p.a_ps,'b_ps':p.b_ps}
        savemat(ROOT/'results/validation/assembly_input.mat',{'y':y,'prior':prior,'settings':{'n_draw':2.,'n_burn':0.,'n_thin':1.,'n_lags':np.full((3,1),3.),'is_timeag':np.zeros((3,1),bool),'i_depend':np.zeros((3,1))}})
        assembly_command = "addpath('results/validation'); d=load('results/validation/assembly_input.mat'); a=reference_matrices(d.y,d.prior,d.settings); save('results/validation/assembly_reference.mat','a','-v7');"
        subprocess.run([str(octave),'--quiet','--eval',assembly_command],cwd=ROOT,check=True)
        reference = loadmat(ROOT/'results/validation/assembly_reference.mat',simplify_cells=True)['a']
        initial = MCT(y,seed=87)
        for label,states in [('SSM',initial.states),('SSM_TVC',initial.loadings)]:
            m = states.model
            for ours,theirs in [('transition','F'),('selection','G')]:
                np.testing.assert_allclose(np.squeeze(getattr(m,ours)),reference[label][theirs],atol=1e-14)
            np.testing.assert_allclose(m.initialization.stationary_cov,reference[label]['Sigma_1'],atol=1e-14)
        np.testing.assert_allclose(initial.states.model.design,reference['SSM']['H'],atol=1e-14)
        np.testing.assert_allclose(initial.states.model.state_cov[:,:,:-1],reference['SSM']['Sigma_eta'],atol=1e-14)
        report['official_state_matrix_assembly'] = 'PASS'
        command = "addpath('upstream/functions'); for c={'initial','latent','loadings','volatility'}; name=c{1}; d=load(['results/validation/' name '_input.mat']); [~,states]=fast_smoother(d.Y,d.SSM); save(['results/validation/' name '_octave.mat'],'states','-v7'); end;"
        subprocess.run([str(octave),'--quiet','--eval',command],cwd=ROOT,check=True)
        for name in ['initial','latent','loadings','volatility']:
            python = loadmat(ROOT/f'results/validation/{name}_python.mat')['states']
            original = loadmat(ROOT/f'results/validation/{name}_octave.mat')['states'].T
            np.testing.assert_allclose(python,original,atol=1e-7,rtol=1e-7)
            report['official_smoother_comparisons'][name] = {'status':'PASS','maximum_absolute_error':float(np.max(abs(python-original)))}
    (ROOT/'results/validation/python_validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


# %% Validation command-line entry point
# Run package-only checks by default or add independent upstream comparisons when
# an Octave executable path is supplied.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--octave',type=Path)
    validate(parser.parse_args().octave)
