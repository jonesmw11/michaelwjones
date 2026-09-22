@echo off
rem =============================================================================
rem %% Launch the MCT monitor with a process-only PowerShell policy bypass.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_mct_progress.ps1" %*
