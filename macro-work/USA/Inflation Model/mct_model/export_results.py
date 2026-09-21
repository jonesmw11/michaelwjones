# Export only locally estimated results, with explicit run status and reference provenance.
#
# MCT PIPELINE MAP
# [1] Source data -> prepare_inputs.py -> data/*.mat
# [2] Python entry -> run_pipeline.py -> run_python.py
# [3] Model engine -> mct_python.py -> posterior draws in results/python/*.mat
# [4] Reporting -> export_results.py -> CSV / XLSX / PNG / JSON
# [5] Optional validation/reference tooling -> Archive/
# Archived Octave route and downloaded research material are not used in production.
#
# THIS FILE: STAGE 4, REPORTING AND EXPORT.
# It validates one completed raw result and creates labelled tables, diagnostics,
# a workbook, and a chart without rerunning the sampler.

# %% Imports and non-interactive plotting setup
# Load command-line, file, numerical, table, MAT-file, and plotting utilities;
# select a headless plotting backend suitable for automated runs.
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


# %% Load and validate the completed model result
# Read one final MAT result and reject files that do not use the production settings.
def load_final_result(path):
    result = loadmat(path, simplify_cells=True)
    settings = result['settings']
    sampling = (
        int(settings['n_draw']),
        int(settings['n_burn']),
        int(settings['n_thin']),
    )
    required_sampling = (3000, 3000, 2)
    if sampling != required_sampling:
        raise ValueError(
            'Final MCT exports require 3,000 retained draws, '
            '3,000 burn-in iterations and thinning of 2.'
        )
    return result


# %% Prepare the shared tables and diagnostics
# Convert raw arrays into labelled tables once, ready for every output format.
def prepare_export(path, result):
    settings = result['settings']
    dates = pd.to_datetime(np.asarray(result['month_codes'], dtype=int).astype(str), format='%Y%m')
    frame = pd.DataFrame(result['MCT'], index=dates, columns=['lower_16.67pct', 'MCT_median', 'upper_83.33pct'])
    frame.index.name = 'Date'
    reference = pd.read_csv(ROOT / 'data/reference_202310.csv', index_col=0, parse_dates=True)
    comparison = frame.join(reference.add_prefix('NYFed_Oct2023_'))
    comparison['difference_pp'] = comparison.MCT_median-comparison.NYFed_Oct2023_median
    vintage = 'replication_202310' if path.stem.startswith('replication') else 'current_reconstruction'
    inputs = loadmat(ROOT / 'data' / f'{vintage}.mat', simplify_cells=True)
    labels = list(inputs['labels'])
    weights = pd.DataFrame(inputs['weights'], index=dates, columns=labels)
    np.testing.assert_allclose(weights.sum(axis=1), 1, atol=1e-12)
    assert np.isfinite(frame.to_numpy()).all()
    assert (frame.iloc[:,0] <= frame.iloc[:,1]).all() and (frame.iloc[:,1] <= frame.iloc[:,2]).all()
    diagnostics = {
        'engine': str(result.get('engine', 'MATLAB / Octave upstream estimator')),
        'status': 'Full official sampling settings; convergence not established by a single chain',
        'vintage': vintage, 'draws': int(settings['n_draw']),
        'burn_in': int(settings['n_burn']), 'thinning': int(settings['n_thin']),
        'elapsed_seconds': float(result['elapsed_seconds']),
        'latest_date': str(dates[-1].date()), 'latest_median': float(frame.MCT_median.iloc[-1]),
        'reference_comparison': 'Same October 2023 input vintage' if vintage.startswith('replication') else 'Different vintages and reconstructed housing input: differences are not pure replication error',
        'reference_rmse_pp': float(np.sqrt(np.nanmean(comparison.difference_pp**2))),
        'reference_mean_absolute_error_pp': float(np.nanmean(abs(comparison.difference_pp))),
        'convergence': 'Not established. Run independent chains and inspect mixing before relying on estimates.',
    }
    return {
        'path': path,
        'result': result,
        'dates': dates,
        'frame': frame,
        'reference': reference,
        'comparison': comparison,
        'inputs': inputs,
        'labels': labels,
        'weights': weights,
        'diagnostics': diagnostics,
        'vintage': vintage,
    }


# %% Export each result format
# Each function below owns one output, making individual exports easy to change.
def export_json(report):
    report['path'].with_suffix('.json').write_text(
        json.dumps(report['diagnostics'], indent=2)
    )


def export_csv(report):
    path = report['path']
    report['frame'].to_csv(path.with_name(path.stem + '_labelled.csv'))


def export_excel(report):
    path = report['path']
    diagnostics = report['diagnostics']
    dates = report['dates']
    labels = report['labels']
    result = report['result']
    inputs = report['inputs']
    with pd.ExcelWriter(path.with_suffix('.xlsx'), engine='xlsxwriter', datetime_format='yyyy-mm') as writer:
        pd.DataFrame(list(diagnostics.items()), columns=['Field','Value']).to_excel(writer, sheet_name='Read me', index=False)
        report['frame'].to_excel(writer, sheet_name='Estimated MCT')
        report['comparison'].to_excel(writer, sheet_name='NY Fed comparison')
        report['weights'].to_excel(writer, sheet_name='Core weights sum to 1')
        pd.DataFrame(inputs['y'], index=dates, columns=labels).to_excel(writer, sheet_name='Sector inflation inputs')
        pd.DataFrame(result['sector_trend'], index=dates, columns=labels).to_excel(writer, sheet_name='Sector trend medians')
        pd.DataFrame(result['sector_contribution'], index=dates, columns=labels).to_excel(writer, sheet_name='Contribution medians')
        for sheet in writer.sheets.values():
            sheet.freeze_panes(1,1)
            sheet.set_column(0,0,16)
            sheet.set_column(1,18,20)
        writer.sheets['Read me'].set_column(1,1,110)


def export_chart(report):
    dates = report['dates']
    frame = report['frame']
    fig, ax = plt.subplots(figsize=(12,5))
    ax.plot(dates, frame.MCT_median, label='Local estimate')
    ax.fill_between(dates, frame.iloc[:,0], frame.iloc[:,2], alpha=.2, label='Central 66.7% posterior interval')
    ax.plot(report['reference'].index, report['reference']['median'], lw=1, label='NY Fed: October 2023 vintage')
    ax.axhline(2, color='#B5651D', lw=1.3, ls=':', label='2% PCE inflation target')
    ax.set(title=f"MCT: {report['vintage']}", ylabel='Annualized inflation, percent')
    ax.legend()
    fig.tight_layout()
    fig.savefig(report['path'].with_suffix('.png'), dpi=160)
    plt.close(fig)


# %% Coordinate the complete export
# Run the shared preparation once, then call each independent output function.
def export(path):
    result = load_final_result(path)
    report = prepare_export(path, result)
    export_json(report)
    export_csv(report)
    export_excel(report)
    export_chart(report)
    print(json.dumps(report['diagnostics'], indent=2))


# %% Standalone command-line exporter
# Accept an existing result MAT path so reports can be regenerated without running
# input preparation or MCMC estimation again.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('result', type=Path)
    export(parser.parse_args().result.resolve())
