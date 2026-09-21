# Preserve upstream sources; add only a corrected function name and console progress.
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
# THIS FILE: OPTIONAL OCTAVE STAGE A, RUNTIME PREPARATION.
# It creates a headless adapter around the preserved upstream MATLAB estimator.

# %% Imports and source location
# Load file, hashing, and JSON utilities; locate the unmodified upstream function.
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
source = ROOT / 'upstream/functions/estimate_MCT.m'

# %% Create the headless Octave-compatible source
# Rename the copied function to match its generated filename and inject textual
# progress output without changing the numerical estimation statements.
text = source.read_text()
text = text.replace('function output = estimate_MCT_new(', 'function output = estimate_MCT_headless(', 1)
needle = 'for i_draw = (-n_burn):n_draw'
assert text.count(needle) == 1
text = text.replace(needle, "progress_clock = tic;\n" + needle + "\n    if mod(i_draw+n_burn,10)==0\n        fprintf('ITERATION %d/%d elapsed %.1f seconds\\n',i_draw+n_burn, n_burn+n_draw, toc(progress_clock));\n        if exist('OCTAVE_VERSION','builtin'), fflush(stdout); end\n    end")

# %% Save the generated runtime and provenance manifest
# Write the adapted function separately from upstream and record its source hash
# and exact intended modifications for reproducibility.
(ROOT / 'runtime').mkdir(exist_ok=True)
(ROOT / 'runtime/estimate_MCT_headless.m').write_text(text)
(ROOT / 'runtime/patch_manifest.json').write_text(json.dumps({
    'upstream_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'changes': ['Rename function to match generated filename', 'Add console progress every ten iterations; no numerical changes'],
}, indent=2))
