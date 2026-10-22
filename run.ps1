# One command: set up (first run only) and start Scam Sentinel.
#   powershell -ExecutionPolicy Bypass -File .\run.ps1          # start the app
#   powershell -ExecutionPolicy Bypass -File .\run.ps1 -Test    # run the offline test suite instead
param([switch]$Test)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "First run: creating .venv and installing requirements..."
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
    & .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
}
if (-not (Test-Path ".env") -and -not $env:GNANI_API_KEY) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Put your Gnani API key in it (or paste it in the app sidebar)."
}
if ($Test) {
    & .\.venv\Scripts\python.exe -m pytest -q -p no:warnings
} else {
    & .\.venv\Scripts\streamlit.exe run app.py
}
