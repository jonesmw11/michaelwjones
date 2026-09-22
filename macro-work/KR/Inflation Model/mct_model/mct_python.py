# Python translation of the published NY Fed monthly, independent-sector configuration.
# Upstream BSD-3-Clause license and attribution are retained in this folder's LICENSE.
# statsmodels implements all Kalman filtering and Gaussian simulation smoothing.
#
# MCT PIPELINE MAP
# [1] Source data -> prepare_inputs.py -> data/*.mat
# [2] Python entry -> run_pipeline.py -> run_python.py
# [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
# [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
# [5] Optional validation/reference tooling -> Archive/
# Archived Octave route and downloaded research material are not used in production.
#
# THIS FILE: STAGE 3, MODEL ENGINE.
# It defines the state-space systems and blocked Gibbs sampler used by run_python.py.

# %% Imports and dependencies
from dataclasses import dataclass
import time
import numpy as np
from scipy.linalg import block_diag, pinvh
from scipy.special import softmax
from statsmodels.tsa.statespace.simulation_smoother import SimulationSmoother


# %% Prior configuration
# =============================================================================
# PRIOR CONFIGURATION
# Collects the fixed hyperparameters that regularize the MA coefficients,
# time-varying loadings, stochastic volatilities, and outlier probabilities.
# =============================================================================
@dataclass(frozen=True)
class Priors:
    prec_ma: float = 0.1
    nu_lam: float = 12
    s2_lam: float = 0.25**2 / 60 / 12
    nu_gam: float = 60
    s2_gam: float = 1 / 60 / 12
    a_ps: float = (1 - 1 / 48) * 120
    b_ps: float = 120 / 48


# %% Time-varying diagonal covariance construction
# =============================================================================
# TIME-VARYING DIAGONAL COVARIANCE CONSTRUCTION
# Converts a T-by-k array of standard deviations or variances into the k-by-k-by-T
# diagonal matrix sequence expected by the state-space implementation.
# =============================================================================
def diagonal_path(values):
    values = np.asarray(values)
    out = np.zeros((values.shape[1], values.shape[1], values.shape[0]))
    i = np.arange(values.shape[1])
    out[i, i, :] = values.T
    return out


# %% Generic linear-Gaussian state-path sampler
# =============================================================================
# GENERIC LINEAR-GAUSSIAN STATE-PATH SAMPLER
# Wraps statsmodels' simulation smoother. Other MCT blocks configure its design
# and covariance matrices, then use it to draw a complete conditional state path.
# =============================================================================
class GaussianStates:
    # This wrapper only maps NY Fed matrices to statsmodels conventions.

    # -------------------------------------------------------------------------
    # INITIALIZE A STATE-SPACE SYSTEM
    # Binds the observations and installs the time-invariant transition,
    # disturbance-selection, and initial-state covariance matrices.
    # -------------------------------------------------------------------------
    def __init__(self, y, transition, selection, initial_cov):
        self.transition,self.selection,self.initial_cov = transition,selection,initial_cov
        self.model = SimulationSmoother(y.shape[1], transition.shape[0], selection.shape[1])
        self.model.bind(np.ascontiguousarray(y, dtype=float))
        self.model['transition'] = transition
        self.model['selection'] = selection
        self.model.initialize_known(np.zeros(transition.shape[0]), np.asarray(initial_cov,dtype=float))
        self.sampler = None

    # -------------------------------------------------------------------------
    # CONFIGURE THE CURRENT GIBBS CONDITIONAL
    # Replaces the observation design and covariance matrices with values implied
    # by the other current Gibbs blocks; optionally replaces pseudo-observations.
    # -------------------------------------------------------------------------
    def configure(self, design, state_cov, obs_cov, y=None):
        if y is not None:
            # Recreate the package model when the Gibbs pseudo-observations change.
            # statsmodels caches its compiled representation of the bound data.
            self.__init__(y,self.transition,self.selection,self.initial_cov)
        self.model['design'] = design
        self.model['state_cov'] = state_cov
        self.model['obs_cov'] = obs_cov

    # -------------------------------------------------------------------------
    # DRAW A COMPLETE LATENT PATH
    # Uses Kalman-based simulation smoothing to sample jointly from the Gaussian
    # conditional distribution of every state at every date.
    # -------------------------------------------------------------------------
    def draw(self, rng):
        if self.sampler is None:
            self.sampler = self.model.simulation_smoother(simulation_output=1)
        self.sampler.simulate(random_state=rng)
        return self.sampler.simulated_state.T.copy()


# %% Conjugate scale-parameter update
# =============================================================================
# CONJUGATE SCALE-PARAMETER UPDATE
# Draws a standard deviation whose squared value has an inverse-gamma posterior.
# It is used for loading smoothness (lambda) and volatility smoothness (gamma).
# =============================================================================
def draw_scale_parameter(x, nu, s2, rng):
    posterior_nu = nu + len(x)
    posterior_ss = nu * s2 + np.sum(x*x, axis=0)
    return 1 / np.sqrt(rng.gamma(posterior_nu / 2, 2 / posterior_ss))


# %% Discrete mixture-indicator update
# =============================================================================
# DISCRETE MIXTURE-INDICATOR UPDATE
# Combines a log likelihood with prior category probabilities, normalizes with a
# softmax, and samples one category for each observation.
# =============================================================================
def mixture_choice(log_likelihood, prior, rng):
    log_prob = log_likelihood + np.log(prior)
    missing = np.isnan(log_prob).any(axis=-1)
    log_prob[missing] = np.broadcast_to(np.log(prior), log_prob.shape)[missing]
    probs = softmax(log_prob, axis=-1)
    return rng.multinomial(1, probs).argmax(axis=-1)


# %% Moving-average coefficient update
# =============================================================================
# MOVING-AVERAGE COEFFICIENT UPDATE
# Draws one sector's MA coefficients from a Gaussian conditional regression and
# applies the upstream root transformation that enforces its MA convention.
# =============================================================================
def draw_ma(y, x, precision, rng):
    q = x.shape[1]
    covariance = pinvh(np.diag(precision*np.arange(1, q+1)**2) + x.T @ x)
    theta = rng.multivariate_normal(covariance @ x.T @ y, covariance)
    # Match the upstream root transformation, including coefficient order.
    roots = np.roots(np.r_[theta[::-1], 1.0])
    outside = abs(roots) > 1
    roots[outside] = 1 / roots[outside]
    coefficients = np.real_if_close(np.poly(roots)[1:])
    return np.pad(coefficients, (0, q-len(coefficients)))


# %% Stochastic-volatility path sampler
# =============================================================================
# STOCHASTIC-VOLATILITY PATH SAMPLER
# Uses a ten-component normal-mixture approximation to log chi-squared noise so
# that a log-volatility path can be drawn as a Gaussian state-space block.
# =============================================================================
class VolatilitySampler:
    probabilities = np.array([.00609,.04775,.13057,.20674,.22715,.18842,.12047,.05591,.01575,.00115])
    means = np.array([1.92677,1.34744,.73504,.02266,-.85173,-1.97278,-3.46788,-5.55246,-8.68384,-14.65000])
    variances = np.array([.11265,.17788,.26768,.40611,.62699,.98583,1.57469,2.54498,4.16591,7.33342])

    # -------------------------------------------------------------------------
    # INITIALIZE THE LOG-VOLATILITY STATE MODEL
    # Creates a one-dimensional random-walk state with the requested uncertainty
    # for its initial log variance.
    # -------------------------------------------------------------------------
    def __init__(self, length, initial_variance):
        self.states = GaussianStates(np.zeros((length+1,1)), np.ones((1,1)), np.ones((1,1)), np.array([[initial_variance]]))

    # -------------------------------------------------------------------------
    # DRAW ONE COMPLETE VOLATILITY PATH
    # Samples mixture labels conditional on current standardized shocks, then
    # simulation-smooths log variance and transforms it back to standard deviation.
    # -------------------------------------------------------------------------
    def draw(self, shocks, sigma, gamma, rng):
        logged = np.log(shocks**2 + 1e-3)
        residual = logged - 2*np.log(sigma)
        likelihood = -.5*(residual[:,None]-self.means)**2/self.variances - .5*np.log(self.variances)
        components = mixture_choice(likelihood, self.probabilities, rng)
        y = np.r_[np.nan, logged-self.means[components]][:,None]
        observation_variance = np.r_[1.,self.variances[components]][None,None,:]
        self.states.configure(np.ones((1,1)), np.array([[gamma**2]]), observation_variance, y)
        return np.exp(self.states.draw(rng)[1:,0]/2)


# %% Multivariate Core Trend model and blocked Gibbs sampler
# =============================================================================
# MULTIVARIATE CORE TREND MODEL AND BLOCKED GIBBS SAMPLER
# Holds the observed sector inflation data, all current latent states and
# parameters, the MCT state-space matrices, and the systematic update schedule.
# =============================================================================
class MCT:
    # Official driver: q=3, no time aggregation, no cross-dependent sectors.

    # -------------------------------------------------------------------------
    # INITIALIZE DATA, PARAMETERS, AND STATE-SPACE STRUCTURES
    # Sets starting values for every Gibbs block and constructs separate smoothers
    # for the main inflation states, time-varying loadings, and volatility paths.
    # -------------------------------------------------------------------------
    def __init__(self, y, seed=2022, priors=None):
        self.y = np.asarray(y, dtype=float)
        if not np.isfinite(self.y).all() or self.y.ndim != 2:
            raise ValueError('This implementation requires a complete monthly input matrix.')
        self.T, self.n = self.y.shape
        self.q, self.skip = 3, 4
        self.priors = priors or Priors()
        p, n, T = self.priors, self.n, self.T
        self.rng = np.random.default_rng(seed)
        # Keep filtered-state sampling off the Gibbs-chain random stream so the
        # diagnostic does not alter the established smoothed MCT results.
        self.filtered_rng = np.random.default_rng(
            np.random.SeedSequence([seed, 0x46494C54])
        )
        self.alpha_tau = np.tile(self.y.std(axis=0, ddof=1)/16, (T,1))
        self.alpha_eps = self.alpha_tau.copy()
        self.sigma_dtau_c = np.ones(T)
        self.sigma_dtau_i = self.alpha_tau.copy()
        self.sigma_eps_c = np.ones(T)
        self.sigma_eps_i = self.alpha_tau.copy()
        self.s_eps_c, self.s_eps_i = np.ones(T), np.ones((T,n))
        self.theta = np.zeros((n,self.q))
        self.lam_tau = np.full(n,np.sqrt(p.s2_lam))
        self.lam_eps = self.lam_tau.copy()
        self.gam_dtau_c = self.gam_eps_c = np.sqrt(p.s2_gam)
        self.gam_dtau_i = np.full(n,np.sqrt(p.s2_gam))
        self.gam_eps_i = self.gam_dtau_i.copy()
        self.scale_values = np.r_[1.,np.linspace(2,10,39)]
        self.s_probs_c = self.scale_probabilities(p.a_ps/(p.a_ps+p.b_ps))
        self.s_probs_i = np.tile(self.s_probs_c,(n,1))
        self.ec = n+1
        self.ei = n+2+np.arange(n)*4
        self.nstates = n+2+4*n
        transition = np.zeros((self.nstates,self.nstates))
        transition[np.arange(n+1),np.arange(n+1)] = 1
        for start in self.ei:
            transition[start+np.arange(1,4),start+np.arange(3)] = 1
        selection = np.zeros((self.nstates,2*(n+1)))
        shock_rows = np.r_[np.arange(n+1),self.ec,self.ei]
        selection[shock_rows,np.arange(len(shock_rows))] = 1
        initial_cov = np.eye(self.nstates)
        initial_cov[0,0] = initial_cov[self.ec,self.ec] = 0
        initial_cov[np.arange(1,n+1),np.arange(1,n+1)] = 11
        self.states = GaussianStates(np.vstack([np.full((1,n),np.nan),self.y]),transition,selection,initial_cov)
        tv_transition = block_diag(np.eye(2*n),transition[n+2:,n+2:])
        tv_selection = np.zeros((6*n,3*n))
        tv_selection[np.r_[np.arange(2*n),2*n+4*np.arange(n)],np.arange(3*n)] = 1
        tv_initial = np.eye(6*n)
        tv_initial[:n,:n] += 10*np.eye(n)
        tv_initial[n:2*n,n:2*n] += 10*np.ones((n,n))
        self.loadings = GaussianStates(self.y.copy(),tv_transition,tv_selection,tv_initial)
        self.vol_common = VolatilitySampler(T,0)
        self.vol_specific = VolatilitySampler(T,100)
        self.refresh_states(initial=True)

    # -------------------------------------------------------------------------
    # CONVERT AN ORDINARY-SHOCK PROBABILITY INTO SCALE-MIXTURE PROBABILITIES
    # Assigns probability p to scale 1 and spreads probability 1-p uniformly over
    # the 39 candidate outlier scales.
    # -------------------------------------------------------------------------
    @staticmethod
    def scale_probabilities(ps):
        ps = np.asarray(ps)
        return np.concatenate([ps[...,None], np.broadcast_to((1-ps)[...,None]/39,ps.shape+(39,))],axis=-1)

    # -------------------------------------------------------------------------
    # BUILD THE SECTOR MA(3) OBSERVATION MATRIX
    # Places each sector's coefficients (1, theta_1, theta_2, theta_3) into one
    # block-diagonal matrix acting on current and lagged idiosyncratic shocks.
    # -------------------------------------------------------------------------
    def theta_block(self):
        return block_diag(*[np.r_[1.,theta][None,:] for theta in self.theta])

    # -------------------------------------------------------------------------
    # CONFIGURE THE MAIN TREND AND TRANSITORY STATE BLOCK
    # Installs the observation and disturbance matrices implied by the current
    # loadings, volatilities, outlier scales, and MA coefficients.
    # -------------------------------------------------------------------------
    def configure_main_states(self, initial=False):
        n,T = self.n,self.T
        design = np.zeros((n,self.nstates,T+1))
        design[:,0,1:] = self.alpha_tau.T
        design[:,1:n+1,1:] = np.eye(n)[:,:,None]
        design[:,self.ec,1:] = self.alpha_eps.T
        design[:,n+2:,1:] = self.theta_block()[:,:,None]
        if not initial:
            design[:,:,0] = design[:,:,1]
        sigmas = np.column_stack([self.sigma_dtau_c,self.sigma_dtau_i,self.sigma_eps_c*self.s_eps_c,self.sigma_eps_i*self.s_eps_i])
        # statsmodels Q[t] drives the transition from state t to t+1.
        covariance = diagonal_path(np.vstack([sigmas,sigmas[-1]])**2)
        self.states.configure(design,covariance,1e-6*np.eye(n))

    # -------------------------------------------------------------------------
    # DRAW THE MAIN TREND AND TRANSITORY STATE BLOCK
    # Draws the entire common and sector-specific state history from the
    # simulation smoother after configuring the current Gibbs conditional.
    # -------------------------------------------------------------------------
    def refresh_states(self, initial=False):
        n = self.n
        self.configure_main_states(initial=initial)
        self.state = self.states.draw(self.rng)
        self.tau_c = self.state[1:,0]
        self.tau_i = self.state[1:,1:n+1]
        self.eps_c = self.state[1:,self.ec]
        self.eps_i = self.state[1:,self.ei]

    # -------------------------------------------------------------------------
    # DRAW THE ONE-SIDED AGGREGATE TREND
    # Runs the ordinary Kalman filter under the current posterior parameter draw
    # and samples each period's aggregate trend from its filtered marginal.
    # Period t therefore uses observations only through t rather than the full sample.
    # -------------------------------------------------------------------------
    def draw_filtered_mct(self, weights):
        self.configure_main_states()
        filtered = self.states.model.filter()
        means = filtered.filtered_state[:,1:].T
        covariances = np.moveaxis(filtered.filtered_state_cov[:,:,1:], -1, 0)
        aggregate_design = np.column_stack([
            np.sum(weights*self.alpha_tau, axis=1),
            weights,
            np.zeros((self.T, self.nstates-self.n-1)),
        ])
        aggregate_mean = np.einsum('ti,ti->t', aggregate_design, means)
        aggregate_variance = np.einsum(
            'ti,tij,tj->t', aggregate_design, covariances, aggregate_design
        )
        aggregate_sd = np.sqrt(np.maximum(aggregate_variance, 0.0))
        return self.filtered_rng.normal(aggregate_mean, aggregate_sd)

    # -------------------------------------------------------------------------
    # PERFORM ONE SYSTEMATIC BLOCKED-GIBBS SWEEP
    # Sequentially updates loading paths, loading smoothness, main latent states,
    # MA coefficients, volatility paths, volatility smoothness, outlier scales,
    # and ordinary-shock probabilities using the latest available block values.
    # -------------------------------------------------------------------------
    def step(self):
        n,T,p,rng = self.n,self.T,self.priors,self.rng
        theta_block = self.theta_block()
        noise_scales = self.sigma_eps_i*self.s_eps_i
        design = np.zeros((n,6*n,T))
        indices = np.arange(n)
        design[indices,indices,:] = self.tau_c
        design[indices,n+indices,:] = self.eps_c
        design[:,2*n:,:] = theta_block[:,:,None]
        sigmas = np.column_stack([np.tile(self.lam_tau,(T,1)),np.tile(self.lam_eps,(T,1)),noise_scales])
        sigmas = np.vstack([sigmas[1:],sigmas[-1]])
        self.loadings.configure(design,diagonal_path(sigmas**2),1e-6*np.eye(n),self.y-self.tau_i)
        loading_states = self.loadings.draw(rng)
        self.alpha_tau,self.alpha_eps = loading_states[:,:n],loading_states[:,n:2*n]
        self.lam_tau = draw_scale_parameter(np.diff(self.alpha_tau[self.skip:],axis=0),p.nu_lam,p.s2_lam,rng)
        self.lam_eps = draw_scale_parameter(np.diff(self.alpha_eps[self.skip:],axis=0),p.nu_lam,p.s2_lam,rng)
        self.refresh_states()
        # MA regressors use the preceding three sector innovations.
        ups = self.state[1:,n+2:] @ theta_block.T
        for i in range(n):
            x = np.column_stack([self.eps_i[self.skip-lag:T-lag,i] for lag in range(1,4)])
            self.theta[i] = draw_ma(ups[self.skip:,i]/noise_scales[self.skip:,i],x/noise_scales[self.skip:,i,None],p.prec_ma,rng)
        dtau_c = np.diff(self.state[:,0])
        dtau_i = np.diff(self.state[:,1:n+1],axis=0)
        dtau_c[:self.skip],dtau_i[:self.skip] = np.nan,np.nan
        ec = self.eps_c/self.s_eps_c
        ei = self.eps_i/self.s_eps_i
        ec[:self.skip],ei[:self.skip] = np.nan,np.nan
        self.sigma_dtau_c = self.vol_common.draw(dtau_c,self.sigma_dtau_c,self.gam_dtau_c,rng)
        for i in range(n):
            self.sigma_dtau_i[:,i] = self.vol_specific.draw(dtau_i[:,i],self.sigma_dtau_i[:,i],self.gam_dtau_i[i],rng)
        self.sigma_eps_c = self.vol_common.draw(ec,self.sigma_eps_c,self.gam_eps_c,rng)
        for i in range(n):
            self.sigma_eps_i[:,i] = self.vol_specific.draw(ei[:,i],self.sigma_eps_i[:,i],self.gam_eps_i[i],rng)
        for label in ['dtau_c','dtau_i','eps_c','eps_i']:
            sigma = getattr(self,'sigma_'+label)
            gamma = draw_scale_parameter(2*np.diff(np.log(sigma[self.skip:]),axis=0),p.nu_gam,p.s2_gam,rng)
            setattr(self,'gam_'+label,gamma)
        for label in ['c','i']:
            x = getattr(self,'eps_'+label)/getattr(self,'sigma_eps_'+label)
            x[:self.skip] = np.nan
            prior = getattr(self,'s_probs_'+label)
            likelihood = -.5*(x[...,None]/self.scale_values)**2-np.log(self.scale_values)
            scales = self.scale_values[mixture_choice(likelihood,prior,rng)]
            setattr(self,'s_eps_'+label,scales)
            n_one = np.sum(scales[self.skip:]==1,axis=0)
            ps = rng.beta(p.a_ps+n_one,p.b_ps+T-self.skip-n_one)
            setattr(self,'s_probs_'+label,self.scale_probabilities(ps))

    # -------------------------------------------------------------------------
    # RUN BURN-IN, RETAIN POSTERIOR DRAWS, AND FORM THE REPORTED MCT
    # Repeats complete Gibbs sweeps, stores post-burn-in common and sector-specific
    # trend aggregates, and returns posterior medians and two-thirds intervals.
    # -------------------------------------------------------------------------
    def sample(self, weights, draws=3000, burn=3000, thin=2, callback=None):
        start = time.perf_counter()
        common = np.empty((self.T,draws))
        specific = np.empty_like(common)
        filtered = np.empty_like(common)
        sector = np.empty((self.T,self.n,draws))
        for iteration in range(-burn,draws+1):
            for _ in range(thin):
                self.step()
            if iteration > 0:
                trend_c = self.alpha_tau*self.tau_c[:,None]
                sector[:,:,iteration-1] = trend_c+self.tau_i
                common[:,iteration-1] = np.sum(weights*trend_c,axis=1)
                specific[:,iteration-1] = np.sum(weights*self.tau_i,axis=1)
                filtered[:,iteration-1] = self.draw_filtered_mct(weights)
            if callback and ((iteration+burn)%10==0 or iteration==draws):
                callback(iteration+burn+1,burn+draws+1,time.perf_counter()-start)
        total = common+specific
        # MATLAB quantile uses the type-5 (Hazen) convention.
        quantiles = lambda x: np.quantile(x,[1/6,.5,5/6],axis=1,method='hazen').T
        return {'MCT':quantiles(total),'MCT_filtered':quantiles(filtered),
                'MCT_common':quantiles(common),'MCT_specific':quantiles(specific),
                'sector_trend':np.median(sector,axis=2),'sector_contribution':np.median(weights[:,:,None]*sector,axis=2),
                'mct_draws':total,'elapsed_seconds':time.perf_counter()-start}
