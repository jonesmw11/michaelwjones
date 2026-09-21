# MCT archive

This folder contains material that is not required by the current Python production path:

`prepare_inputs.py -> run_pipeline.py -> run_python.py -> mct_python.py -> export_results.py`

Nothing was deleted. The archived material is grouped as follows:

- `Documentation/`: the locally written MCT guide and downloaded papers/web references.
- `Validation/`: the optional Python/Octave validation driver and generated comparison fixtures.
- `Octave/`: the optional MATLAB/Octave driver, generated runtime adapter, upstream MATLAB functions, reference workbook, and old Octave smoke-test outputs.
- `Python_Results/replication_202310/`: completed Python result sets for the archived October 2023 replication vintage.
- `Python_Results/current_reconstruction_smoke_tests/`: five- and ten-draw current-data execution tests plus the completed run's console logs. These are diagnostic records, not active inflation estimates.
- `Generated/`: disposable Python bytecode caches.

The active `upstream/` folder intentionally retains the official input MAT file, official result MAT file, and license because `prepare_inputs.py` reads those two data files and the Python port retains the upstream license attribution.

Archived scripts preserve their contents for reference, but their original relative paths are no longer active. Restore them to their former locations before attempting the archived Octave or validation workflows.
