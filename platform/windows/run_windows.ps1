$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Ambiente .venv nao encontrado. Corre primeiro: .\install_windows.ps1"
    exit 1
}

& $venvPython v3.py
