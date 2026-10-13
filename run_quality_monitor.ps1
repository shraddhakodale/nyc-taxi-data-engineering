$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Starting NYC Taxi quality monitoring..."

python .\monitor_pipeline.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Quality monitoring failed. Check the error output."
    exit 1
}

Write-Host "Quality monitoring completed."
