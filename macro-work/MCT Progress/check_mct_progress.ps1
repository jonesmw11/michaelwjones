param(
    [ValidateSet("ALL", "JP", "AU", "AU_HEADLINE", "KR")]
    [string]$Country = "ALL",
    [switch]$Watch,
    [int]$RefreshSeconds = 10,
    [switch]$NoLog
)

# =============================================================================
# %% Paths and country definitions
$ProgressRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$MacroRoot = Split-Path -Parent $ProgressRoot
$HistoryPath = Join-Path $ProgressRoot "mct_progress_history.csv"
$Models = [ordered]@{
    JP = Join-Path $MacroRoot "JP\Inflation Model\mct_model\results\python"
    AU = Join-Path $MacroRoot "AU\Inflation Model\mct_model_core\results\python"
    AU_HEADLINE = Join-Path $MacroRoot "AU\Inflation Model\mct_model_headline\results\python"
    KR = Join-Path $MacroRoot "KR\Inflation Model\mct_model\results\python"
}


# =============================================================================
# %% Read one model's latest production status
function Get-MctProgress {
    param([string]$Code, [string]$ResultsPath)

    $StatusFile = Get-ChildItem -LiteralPath $ResultsPath -Filter "*_d3000_b3000_t2_s2022_status.json" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $StatusFile) {
        return [pscustomobject]@{
            Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Country = $Code
            Status = "not found"
            Iteration = $null
            Total = $null
            Percent = $null
            Elapsed = $null
            ETA = $null
            Updated = $null
            StatusFile = $null
        }
    }

    try {
        $State = Get-Content -LiteralPath $StatusFile.FullName -Raw | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Country = $Code
            Status = "status file is updating"
            Iteration = $null
            Total = $null
            Percent = $null
            Elapsed = $null
            ETA = $null
            Updated = $StatusFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            StatusFile = $StatusFile.FullName
        }
    }

    $Iteration = if ($null -ne $State.iteration) { [double]$State.iteration } else { 0 }
    $Total = if ($null -ne $State.total) { [double]$State.total } else { 0 }
    $ElapsedSeconds = if ($null -ne $State.elapsed_seconds) { [double]$State.elapsed_seconds } else { 0 }
    $Percent = if ($Total -gt 0) { 100 * $Iteration / $Total } else { 0 }
    $RemainingSeconds = if ($Iteration -gt 0 -and $State.status -eq "running") {
        $ElapsedSeconds * ($Total - $Iteration) / $Iteration
    }
    else {
        0
    }

    [pscustomobject]@{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Country = $Code
        Status = [string]$State.status
        Iteration = [int]$Iteration
        Total = [int]$Total
        Percent = "{0:N1}%" -f $Percent
        Elapsed = ([timespan]::FromSeconds($ElapsedSeconds)).ToString("hh\:mm\:ss")
        ETA = ([timespan]::FromSeconds([math]::Max(0, $RemainingSeconds))).ToString("hh\:mm\:ss")
        Updated = $StatusFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        StatusFile = $StatusFile.FullName
    }
}


# =============================================================================
# %% Display and optionally log snapshots
do {
    $Selected = if ($Country -eq "ALL") { $Models.Keys } else { @($Country) }
    $Snapshot = foreach ($Code in $Selected) {
        Get-MctProgress -Code $Code -ResultsPath $Models[$Code]
    }

    if ($Watch) {
        Clear-Host
    }
    Write-Host "MCT production progress | $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    $Snapshot | Format-Table Country, Status, Iteration, Total, Percent, Elapsed, ETA, Updated -AutoSize

    if (-not $NoLog) {
        $Snapshot | Export-Csv -LiteralPath $HistoryPath -Append -NoTypeInformation
    }

    if ($Watch) {
        Write-Host "Refreshing every $RefreshSeconds seconds. Press Ctrl+C to stop watching." -ForegroundColor DarkGray
        Start-Sleep -Seconds $RefreshSeconds
    }
} while ($Watch)
