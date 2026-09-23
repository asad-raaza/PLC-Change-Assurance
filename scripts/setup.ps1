# Local lab setup. Do not use these secrets outside the testbed.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m pip install -r requirements.txt
$env:PYTHONPATH = "backend;."
New-Item -ItemType Directory -Force -Path data | Out-Null
python -m scripts.seed
Set-Location frontend
if (-not (Test-Path node_modules)) { npm install }
Write-Host "Setup complete. Start API: python -m uvicorn app.main:app --app-dir backend --reload"
Write-Host "Start UI:  cd frontend; npm run dev"
