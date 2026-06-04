param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Join-Path $PSScriptRoot "..")

$name = "sic-opto-downloader"
if ($Version) {
    $name = "$name-$Version"
}
$exeName = "$name-windows"

python -m pip install --upgrade pip
python -m pip install pyinstaller yt-dlp requests pywidevine selenium websocket-client

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", $exeName,
    "--collect-all", "pywidevine",
    "--collect-all", "pymp4",
    "--collect-all", "google",
    "v3.py"
)

if (Test-Path -LiteralPath "assets\app-icon.ico") {
    $pyinstallerArgs = @("--icon", "assets\app-icon.ico") + $pyinstallerArgs
}

python -m PyInstaller @pyinstallerArgs

New-Item -ItemType Directory -Force -Path "release-dist" | Out-Null
Copy-Item -Force "dist\$exeName.exe" "release-dist\$exeName.exe"

Write-Host "EXE criado: release-dist\$exeName.exe"
