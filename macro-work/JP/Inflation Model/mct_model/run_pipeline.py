# Default entry point for the self-contained country MCT pipeline.

# =============================================================================
# %% Forward command-line execution
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("run_python.py")), run_name="__main__")
