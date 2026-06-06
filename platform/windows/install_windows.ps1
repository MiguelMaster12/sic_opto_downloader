param(
    [switch]$NoRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Find-Python {
    $commands = @(
        @("py", "-3"),
        @("python", ""),
        @("python3", "")
    )

    foreach ($cmd in $commands) {
        $exe = $cmd[0]
        $arg = $cmd[1]
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            try {
                if ($arg) {
                    & $exe $arg -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
                } else {
                    & $exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
                }
                if ($LASTEXITCODE -eq 0) {
                    if ($arg) { return @($exe, $arg) }
                    return @($exe)
                }
            } catch {
            }
        }
    }

    throw "Python 3.9+ nao encontrado. Instala Python e volta a correr este script."
}

Write-Host ""
Write-Host "=== Opto Downloader - Instalador Windows ==="
Write-Host ""

$python = Find-Python
$pythonExe = $python[0]
$pythonArgs = @()
if ($python.Count -gt 1) {
    $pythonArgs = @($python | Select-Object -Skip 1)
}

if (-not (Test-Path -LiteralPath ".venv")) {
    Write-Host "A criar ambiente virtual .venv..."
    & $pythonExe @pythonArgs -m venv .venv
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Ambiente virtual invalido: $venvPython"
}

Write-Host "A atualizar pip..."
& $venvPython -m pip install --upgrade pip

Write-Host "A instalar e configurar dependencias..."
& $venvPython instalar_dependencias.py

if ($LASTEXITCODE -ne 0) {
    throw "O instalador Python terminou com erro."
}

Write-Host ""
Write-Host "[OK] Instalacao concluida."
Write-Host "Para abrir: .\run_windows.ps1"
Write-Host ""

if (-not $NoRun) {
    $answer = Read-Host "Abrir a ferramenta agora? [s/N]"
    if ($answer -match "^[sSyY]") {
        & (Join-Path $PSScriptRoot "run_windows.ps1")
    }
}
