function run_mct(vintage, n_draw, n_burn, n_thin, seed)
% Run the official estimator with a compact, headless output pipeline.
%
% MCT PIPELINE MAP
% [1] Source data -> prepare_inputs.py -> data/*.mat
% [2] Python entry -> run_pipeline.py -> run_python.py
% [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
% [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
% [5] Validation -> validate_python.py
% Optional Octave reference:
% prepare_runtime.py -> run_octave_pipeline.py -> run_mct.m -> export_results.py
%
% THIS FILE: OPTIONAL OCTAVE STAGE C, MATLAB/OCTAVE ESTIMATION DRIVER.
% It configures and calls the preserved estimator, constructs MCT draws, and saves
% a compact raw result for the shared Python reporting stage.

%% Default arguments and Octave/MATLAB environment
% Supply official sampling defaults, locate upstream/runtime functions, disable
% interactive figures, load Octave's statistics package, and initialize the seed.
if nargin < 1, vintage = 'replication_202310'; end
if nargin < 2, n_draw = 3000; end
if nargin < 3, n_burn = 3000; end
if nargin < 4, n_thin = 2; end
if nargin < 5, seed = 2022; end
root = fileparts(mfilename('fullpath'));
addpath(fullfile(root, 'upstream', 'functions'));
addpath(fullfile(root, 'runtime'));
if exist('OCTAVE_VERSION', 'builtin'), pkg('load', 'statistics'); end
set(0, 'defaultfigurevisible', 'off');
rng(seed);

%% Load prepared inputs and configure estimation
% Read one model-ready vintage and define the published MA-lag configuration,
% priors, burn-in, retained draws, thinning, and random seed.
d = load(fullfile(root, 'data', [vintage '.mat']));
n = size(d.y, 2);
settings = struct('n_draw',n_draw,'n_burn',n_burn,'n_thin',n_thin, ...
    'n_lags',repmat(3,n,1),'is_timeag',false(n,1),'i_depend',zeros(n,1));
prior = struct('prec_MA',0.1,'nu_lam',12,'s2_lam',0.25^2/60/12, ...
    'nu_gam',60,'s2_gam',1/60/12,'a_ps',(1-1/48)*120,'b_ps',(1/48)*120);
fprintf('START %s: %d months, %d sectors, draws=%d burn=%d thin=%d seed=%d\n',vintage,size(d.y,1),n,n_draw,n_burn,n_thin,seed);

%% Run the upstream blocked-Gibbs estimator
% Generate the posterior state and parameter draws through the headless copy of
% the official implementation and retain the components needed for MCT reporting.
started = tic;
draws = estimate_MCT_headless(d.y, prior, settings);
elapsed_seconds = toc(started);
alpha_tau = draws.alpha_tau;
tau_c = draws.tau_c;
sector_specific = draws.tau_i;
clear draws;

%% Construct posterior MCT draws and summaries
% Combine common and sector-specific persistent inflation using core expenditure
% weights, then calculate aggregate intervals, trends, and sector contributions.
sector_common = alpha_tau .* permute(repmat(tau_c,1,1,n),[1 3 2]);
clear alpha_tau tau_c;
common = squeeze(sum(d.weights .* sector_common,2));
specific = squeeze(sum(d.weights .* sector_specific,2));
mct_draws = common + specific;
MCT = quantile(mct_draws,[1/6,0.5,5/6],2);
MCT_common = quantile(common,[1/6,0.5,5/6],2);
MCT_specific = quantile(specific,[1/6,0.5,5/6],2);
sector_trend = median(sector_common+sector_specific,3);
sector_contribution = median(d.weights .* (sector_common+sector_specific),3);
month_codes = d.month_codes(:);

%% Save the compact reference-run result
% Write raw posterior summaries and draws for export_results.py, alongside a simple
% CSV and a final console summary.
out = fullfile(root,'results');
if ~exist(out,'dir'), mkdir(out); end
tag = sprintf('%s_d%d_b%d_t%d_s%d',vintage,n_draw,n_burn,n_thin,seed);
save(fullfile(out,[tag '.mat']),'MCT','MCT_common','MCT_specific','sector_trend','sector_contribution','mct_draws','month_codes','prior','settings','seed','elapsed_seconds','-v7');
csvwrite(fullfile(out,[tag '.csv']),[month_codes,MCT,d.headline_yoy(:),d.core_yoy(:)]);
fprintf('FINISHED %.2f seconds; last MCT %.6f [%.6f, %.6f]\n',elapsed_seconds,MCT(end,2),MCT(end,1),MCT(end,3));
end
