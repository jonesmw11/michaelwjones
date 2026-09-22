# MCT production progress

`check_mct_progress.ps1` reads the live JSON status files written independently by the Japan, Australia, and Korea MCT runs. By default, each check appends a timestamped snapshot to `mct_progress_history.csv`.

From the repository root:

```powershell
# Recommended on systems that block PowerShell scripts
& ".\macro-work\MCT Progress\check_mct_progress.cmd" -Country JP -Watch

# Show all three once
& ".\macro-work\MCT Progress\check_mct_progress.cmd"

# Watch one model and refresh every 10 seconds
& ".\macro-work\MCT Progress\check_mct_progress.cmd" -Country JP -Watch

# Watch all models every 30 seconds without adding history rows
& ".\macro-work\MCT Progress\check_mct_progress.cmd" -Watch -RefreshSeconds 30 -NoLog
```

Valid country values are `JP`, `AU`, `AU_HEADLINE`, `KR`, and `ALL`. Stop watch mode with `Ctrl+C`.

`AU` refers to the completed Australian core model. Use `AU_HEADLINE` for the separate longer-history headline model.

The command launcher uses `-ExecutionPolicy Bypass` only for the child PowerShell process. It does not change the user or machine execution policy.
