param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Join-Path $PSScriptRoot "..")

$name = "opto-downloader"
if ($Version) {
    $name = "$name-$Version"
}
$exeName = "$name-windows"

python -m pip install --upgrade pip
python -m pip install pyinstaller PySide6 yt-dlp requests pywidevine

$dataSep = ";"
$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", $exeName,
    "--add-data", "assets${dataSep}assets",
    "--hidden-import", "PySide6.QtMultimedia",
    "--hidden-import", "PySide6.QtMultimediaWidgets",
    "--collect-all", "pywidevine",
    "--collect-all", "pymp4",
    "--collect-all", "google",
    "opto_app.py"
)

if (Test-Path -LiteralPath "assets\app-icon.ico") {
    $pyinstallerArgs = @("--icon", "assets\app-icon.ico") + $pyinstallerArgs
}

python -m PyInstaller @pyinstallerArgs

New-Item -ItemType Directory -Force -Path "release-dist" | Out-Null
Copy-Item -Force "dist\$exeName.exe" "release-dist\$exeName.exe"

Write-Host "EXE criado: release-dist\$exeName.exe"
