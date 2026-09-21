function output = reference_matrices(y, prior, settings)
% ESTIMATE_MCT  Estimate Multivariate Core Trend model
%
% Levels of alpha_tau*tau_c and tau_i are not identified.
% Signs of tau_c, alpha_tau, eps_c, alpha_eps are not identified.

% Determine progress report
if isfield(settings, 'show_progress') 
    show_progress = settings.show_progress; 
    del_str       = '';
    avg_time      = NaN;
    tic    
    fig0          = figure();
    set(fig0, 'units', 'normalized', 'position', [0 0 1 1])
else
    show_progress = false; 
end

% Define function handle
symmetrize = @(A) (A + A')/2;

% Recover settings and dimensions
n_draw = settings.n_draw;
n_burn = settings.n_burn;
n_thin = settings.n_thin;
[T, n] = size(y);
q      = settings.n_lags(:);

% Recover indicators for time-aggregated and cross-dependent series
if isfield(settings, 'is_timeag'), is_timeag = settings.is_timeag; else, is_timeag = false(n, 1); end % which series are time-aggregated
t_skip    = max(q+12*is_timeag)+1;
if isfield(settings, 'i_depend'), i_depend = settings.i_depend; else, i_depend = zeros(n, 1); end % indicator of series with which cross-dependence is allowed
is_depend = (i_depend > 0);

% Set beta prior
if isfield(prior, 'prec_beta'), prec_beta = prior.prec_beta; else, prec_beta = 1; end

% Set theta restrictions and prior
if (length(q) == 1), q = repmat(q, [n, 1]); end
theta_r = ((1:max(q)) <= q);
prec_MA = prior.prec_MA;

% Set lambda/gamma priors
nu_lam = prior.nu_lam;
s2_lam = prior.s2_lam;
nu_gam = prior.nu_gam;
s2_gam = prior.s2_gam;

% Set support for s_eps and ps prior
a_ps     = prior.a_ps;
b_ps     = prior.b_ps;
n_s_vals = 40;
s_vals   = [1; linspace(2, 10, n_s_vals-1)'];

% Preallocate output
output              = struct();
output.tau_c        = NaN(T, n_draw);
output.alpha_tau    = NaN(T, n, n_draw);
output.sigma_dtau_c = NaN(T, n_draw);
output.tau_i        = NaN(T, n, n_draw);
output.sigma_dtau_i = NaN(T, n, n_draw);
output.eps_c        = NaN(T, n_draw);
output.alpha_eps    = NaN(T, n, n_draw);
output.sigma_eps_c  = NaN(T, n_draw);
output.s_eps_c      = NaN(T, n_draw);
output.eps_i        = NaN(T, n, n_draw);
output.sigma_eps_i  = NaN(T, n, n_draw);
output.s_eps_i      = NaN(T, n, n_draw);
output.theta        = NaN(n, max(q), n_draw);
output.lam_tau      = NaN(n, n_draw);
output.beta_tau     = NaN(n, n_draw);
output.gam_dtau_c   = NaN(1, n_draw);
output.gam_dtau_i   = NaN(n, n_draw);
output.lam_eps      = NaN(n, n_draw);
output.beta_eps     = NaN(n, n_draw);
output.gam_eps_c    = NaN(1, n_draw);
output.ps_c         = NaN(1, n_draw);
output.gam_eps_i    = NaN(n, n_draw);
output.ps_i         = NaN(n, n_draw);
output.y_draw       = NaN(T, n, n_draw);

% Initialize latent variables and parameters
if (nargin < 4)
    y_scale      = std(y, 'omitnan');
    alpha_tau    = (y_scale/16).*ones(T, n);
    sigma_dtau_c = ones(T, 1);
    sigma_dtau_i = (y_scale/16).*ones(T, n);
    alpha_eps    = (y_scale/16).*ones(T, n);
    sigma_eps_c  = ones(T, 1);
    s_eps_c      = ones(T, 1);
    sigma_eps_i  = (y_scale/16).*ones(T, n);
    s_eps_i      = ones(T, n);
    theta        = zeros(n, max(q));
    lam_tau      = sqrt(s2_lam)*ones(n, 1);
    beta_tau     = zeros(n, 1);
    gam_dtau_c   = sqrt(s2_gam);
    gam_dtau_i   = sqrt(s2_gam)*ones(n, 1);
    lam_eps      = sqrt(s2_lam)*ones(n, 1);
    beta_eps     = zeros(n, 1);
    gam_eps_c    = sqrt(s2_gam);
    gam_eps_i    = sqrt(s2_gam)*ones(n, 1);
    ps           = a_ps/(a_ps+b_ps);
    s_probs      = [ps, (1-ps)/(n_s_vals-1)*ones(1, n_s_vals-1)];
    s_probs_c    = s_probs;
    s_probs_i    = repmat(s_probs, n, 1);    
else
    alpha_tau     = initial.alpha_tau;
    sigma_dtau_c  = initial.sigma_dtau_c;
    sigma_dtau_i  = initial.sigma_dtau_i;
    alpha_eps     = initial.alpha_eps;
    sigma_eps_c   = initial.sigma_eps_c;
    s_eps_c       = initial.s_eps_c;
    sigma_eps_i   = initial.sigma_eps_i;
    s_eps_i       = initial.s_eps_i;
    theta         = initial.theta;
    lam_tau       = initial.lam_tau;
    if isfield(initial, 'beta_tau'), beta_tau = initial.beta_tau; else, beta_tau = zeros(n, 1); end
    gam_dtau_c    = initial.gam_dtau_c;
    gam_dtau_i    = initial.gam_dtau_i;
    lam_eps       = initial.lam_eps;
    if isfield(initial, 'beta_eps'), beta_eps = initial.beta_eps; else, beta_eps = zeros(n, 1); end
    gam_eps_c     = initial.gam_eps_c;
    gam_eps_i     = initial.gam_eps_i;
    s_probs_c     = [initial.ps_c, (1-initial.ps_c)/(n_s_vals-1)*ones(1, n_s_vals-1)];
    s_probs_i     = [initial.ps_i, (1-initial.ps_i)/(n_s_vals-1)*ones(1, n_s_vals-1)];
end

% Define indexing for state variables
if any(is_timeag), id_tau_c = 1:12; else, id_tau_c = 1; end
id_tmp   = length(id_tau_c);
id_tau_i = cell(n, 1);
for i = 1:n
    if is_timeag(i), id_tau_i{i} = id_tmp+(1:12); else, id_tau_i{i} = id_tmp+1; end
    id_tmp = id_tmp + length(id_tau_i{i});
end
id_eps_c = id_tmp + 1;
id_tmp   = id_tmp + length(id_eps_c);
id_eps_i = cell(n, 1);
for i = 1:n
    id_eps_i{i} = id_tmp + (1:(1+q(i)));
    id_tmp      = id_tmp + length(id_eps_i{i});
end
n_state = id_tmp;

% Define auxiliary variables
eye_cell      = cell(n, 1); for i = 1:n, if is_timeag(i), eye_cell{i} = repmat(1/12, [1, 12]); else, eye_cell{i} = 1; end; end
eye_blk       = blkdiag(eye_cell{:});
theta_cell    = cell(n, 1); for i = 1:n, theta_cell{i} = [1, theta(i, theta_r(i, :))]; end
theta_blk     = blkdiag(theta_cell{:});
sigmaXs_eps_c = sigma_eps_c.*s_eps_c;
sigmaXs_eps_i = sigma_eps_i.*s_eps_i;

% Initialize state-space model
SSM = struct();
%%% H
SSM.H = zeros(n, n_state, T+1);  
for t = 1:T
    SSM.H(~is_timeag, id_tau_c(1), t+1) = alpha_tau(t, ~is_timeag)';
    SSM.H(is_timeag, id_tau_c, t+1)     = (1/12)*[alpha_tau(t:(-1):max(1, t-11), is_timeag)', repmat(alpha_tau(1, is_timeag)', [1, max(12-t, 0)])];
    SSM.H(:, [id_tau_i{:}], t+1)        = eye_blk;
    SSM.H(:, id_eps_c(1), t+1)          = alpha_eps(t, :)';
    SSM.H(:, [id_eps_i{:}], t+1)        = theta_blk;
    for i = 1:n
        if is_depend(i)
            i_aux                          = i_depend(i);
            SSM.H(i, id_tau_i{i_aux}, t+1) = beta_tau(i)*SSM.H(i_aux, id_tau_i{i_aux}, t+1);
            SSM.H(i, id_eps_i{i_aux}, t+1) = beta_eps(i)*SSM.H(i_aux, id_eps_i{i_aux}, t+1);
        end
    end
end
%%% Sigma_eps
SSM.Sigma_eps = (1e-6)*eye(n);
%%% F
SSM.F                     = zeros(n_state);
n_tmp                     = length(id_tau_c);
SSM.F(id_tau_c, id_tau_c) = [1, zeros(1, n_tmp-1); eye(n_tmp-1), zeros(n_tmp-1, 1)];
for i = 1:n
    n_tmp                           = length(id_tau_i{i});
    SSM.F(id_tau_i{i}, id_tau_i{i}) = [1, zeros(1, n_tmp-1); eye(n_tmp-1), zeros(n_tmp-1, 1)]; 
end
n_tmp                     = length(id_eps_c);
SSM.F(id_eps_c, id_eps_c) = [zeros(1, n_tmp); eye(n_tmp-1), zeros(n_tmp-1, 1)];
for i = 1:n
    n_tmp                           = length(id_eps_i{i});
    SSM.F(id_eps_i{i}, id_eps_i{i}) = [zeros(1, n_tmp); eye(n_tmp-1), zeros(n_tmp-1, 1)];
end
%%% G
SSM.G                = zeros(n_state, 2*(n+1));
n_tmp                = length(id_tau_c);
SSM.G(id_tau_c, 1)   = [1; zeros(n_tmp-1, 1)];
for i = 1:n
    n_tmp                   = length(id_tau_i{i});
    SSM.G(id_tau_i{i}, 1+i) = [1; zeros(n_tmp-1, 1)];
end
n_tmp                = length(id_eps_c);
SSM.G(id_eps_c, 2+n) = [1; zeros(n_tmp-1, 1)];
for i = 1:n
    n_tmp                     = length(id_eps_i{i});
    SSM.G(id_eps_i{i}, 2+n+i) = [1; zeros(n_tmp-1, 1)];
end
%%% Sigma_eta
SSM.Sigma_eta = zeros(2*(n+1), 2*(n+1), T);
for t = 1:T
    SSM.Sigma_eta(:, :, t) = diag([sigma_dtau_c(t), sigma_dtau_i(t, :), ...
                                  sigmaXs_eps_c(t), sigmaXs_eps_i(t, :)].^2);    
end
%%% mu_1 and Sigma_1
SSM.mu_1                        = zeros(n_state, 1);
SSM.mu_1(id_tau_c)              = 0;
SSM.Sigma_1                     = zeros(n_state);
for i = 1:n
    SSM.Sigma_1(id_tau_i{i}, id_tau_i{i}) = eye(length(id_tau_i{i})) + 1e1*ones(length(id_tau_i{i}));
    SSM.Sigma_1(id_eps_i{i}, id_eps_i{i}) = eye(length(id_eps_i{i}));
end
SSM.Sigma_1(id_tau_c, id_tau_c) = 0;
SSM.Sigma_1(id_eps_c, id_eps_c) = 0;

% Define indexing for TVCs
id_TVC = cell(n, 1);
id_tmp = 0;
for i = 1:n
    if is_timeag(i), id_TVC{i} = id_tmp + (1:12); else, id_TVC{i} = id_tmp + 1; end
    id_tmp = id_tmp + length(id_TVC{i});
end
n_TVC  = id_tmp;

% Initialize state-space model for TVCs
SSM_TVC = struct();
%%% H
SSM_TVC.H = zeros(n, n_TVC+n+size(theta_blk, 2), T);
%%% Sigma_eps
SSM_TVC.Sigma_eps = (1e-6)*eye(n);
%%% F
SSM_TVC.F = blkdiag(zeros(n_TVC+n), SSM.F([id_eps_i{:}], [id_eps_i{:}]));
for i = 1:n
    n_tmp                           = length(id_TVC{i});
    SSM_TVC.F(id_TVC{i}, id_TVC{i}) = [1, zeros(1, n_tmp-1); eye(n_tmp-1), zeros(n_tmp-1, 1)];
end
SSM_TVC.F(n_TVC+(1:n), n_TVC+(1:n)) = eye(n);
%%% G
SSM_TVC.G = blkdiag(zeros(n_TVC+n, 2*n), SSM.G([id_eps_i{:}], 2+n+(1:n)));
for i = 1:n
    n_tmp                   = length(id_TVC{i});
    SSM_TVC.G(id_TVC{i}, i) = [1; zeros(n_tmp-1, 1)];
end
SSM_TVC.G(n_TVC+(1:n), n+(1:n)) = eye(n);
%%% Sigma_eta
SSM_TVC.Sigma_eta = zeros(3*n, 3*n, T-1);
%%% mu_1 and Sigma_1
SSM_TVC.mu_1    = zeros(n_TVC+n+size(theta_blk, 2), 1);
Sigma_aux       = zeros(n_TVC); for i = 1:n, Sigma_aux(id_TVC{i}, id_TVC{i}) = 1; end
SSM_TVC.Sigma_1 = eye(n_TVC+n+size(theta_blk, 2)) ...
     + 1e1*blkdiag(Sigma_aux, ones(n), zeros(size(theta_blk, 2)));


output.SSM=SSM; output.SSM_TVC=SSM_TVC;
end
