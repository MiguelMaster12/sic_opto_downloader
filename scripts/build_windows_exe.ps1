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

# ---------------------------------------------------------------------------
# 1. Dependências Python
# ---------------------------------------------------------------------------
Write-Host ">> Instalar dependências Python..."
python -m pip install --upgrade pip
python -m pip install pyinstaller PySide6 yt-dlp requests pywidevine

# ---------------------------------------------------------------------------
# 2. Descarregar binários externos (ffmpeg + mp4decrypt)
# ---------------------------------------------------------------------------
$vendorDir = "vendor_build_win"
New-Item -ItemType Directory -Force -Path $vendorDir | Out-Null

# --- ffmpeg ---
$ffmpegZipUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$ffmpegZip    = "$vendorDir\ffmpeg.zip"
$ffmpegOut    = "$vendorDir\ffmpeg"

if (-not (Test-Path "$ffmpegOut\ffmpeg.exe")) {
    Write-Host ">> Descarregar ffmpeg..."
    Invoke-WebRequest -Uri $ffmpegZipUrl -OutFile $ffmpegZip -UseBasicParsing
    Expand-Archive -LiteralPath $ffmpegZip -DestinationPath "$ffmpegOut\_extract" -Force
    # O ZIP tem uma subpasta com o nome do build — encontrá-la dinamicamente
    $inner = Get-ChildItem "$ffmpegOut\_extract" -Directory | Select-Object -First 1
    Copy-Item "$($inner.FullName)\bin\ffmpeg.exe"  "$ffmpegOut\ffmpeg.exe"
    Copy-Item "$($inner.FullName)\bin\ffprobe.exe" "$ffmpegOut\ffprobe.exe"
    Remove-Item "$ffmpegOut\_extract" -Recurse -Force
    Remove-Item $ffmpegZip -Force
    Write-Host "   ffmpeg e ffprobe prontos."
} else {
    Write-Host "   ffmpeg já presente, a saltar download."
}

# --- Bento4 (mp4decrypt) ---
$bento4Url = "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-microsoft-win32.zip"
$bento4Zip = "$vendorDir\bento4.zip"
$bento4Out = "$vendorDir\bento4"

if (-not (Test-Path "$bento4Out\mp4decrypt.exe")) {
    Write-Host ">> Descarregar Bento4 (mp4decrypt)..."
    Invoke-WebRequest -Uri $bento4Url -OutFile $bento4Zip -UseBasicParsing
    Expand-Archive -LiteralPath $bento4Zip -DestinationPath "$bento4Out\_extract" -Force
    $inner = Get-ChildItem "$bento4Out\_extract" -Recurse -Filter "mp4decrypt.exe" | Select-Object -First 1
    Copy-Item $inner.FullName "$bento4Out\mp4decrypt.exe"
    Remove-Item "$bento4Out\_extract" -Recurse -Force
    Remove-Item $bento4Zip -Force
    Write-Host "   mp4decrypt pronto."
} else {
    Write-Host "   mp4decrypt já presente, a saltar download."
}

# ---------------------------------------------------------------------------
# 3. PyInstaller — onedir (sem extração para %TEMP%)
# ---------------------------------------------------------------------------
Write-Host ">> Verificar arquitetura..."
Write-Host "PROCESSOR_ARCHITECTURE: $env:PROCESSOR_ARCHITECTURE"
python -c "import struct; print('Python bits:', struct.calcsize('P')*8)"
python -c "import platform; print('Machine:', platform.machine())"

Write-Host ">> Construir EXE com PyInstaller (onedir)..."

$dataSep = ";"

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onedir",           # pasta fixa em vez de extração para %TEMP%
    "--windowed",
    "--target-arch", "x86_64",
    "--name", $exeName,
    "--distpath", "dist_win",
    "--add-data", "assets${dataSep}assets",
    # Binários externos incluídos na pasta raiz do bundle
    "--add-binary", "$ffmpegOut\ffmpeg.exe${dataSep}.",
    "--add-binary", "$ffmpegOut\ffprobe.exe${dataSep}.",
    "--add-binary", "$bento4Out\mp4decrypt.exe${dataSep}.",
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

# ---------------------------------------------------------------------------
# 4. Empacotar em ZIP para distribuição (7-Zip para evitar corrupção)
# ---------------------------------------------------------------------------
Write-Host ">> Empacotar em ZIP..."
New-Item -ItemType Directory -Force -Path "release-dist" | Out-Null

$zipPath = "release-dist\$exeName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

$7z = "C:\Program Files\7-Zip\7z.exe"
if (-not (Test-Path $7z)) {
    # fallback caso o path seja diferente
    $7z = (Get-Command 7z -ErrorAction SilentlyContinue).Source
}
if (-not $7z) {
    throw "7-Zip nao encontrado. Garante que o step 'Install 7-Zip' correu antes."
}

# Adiciona README de instalacao dentro da pasta antes de zipar
$readmePath = "dist_win\$exeName\LEIA-ME.txt"
Set-Content -Encoding UTF8 $readmePath @"
SIC OPTO Downloader - Instrucoes de instalacao
===============================================

1. Extrai TODA esta pasta para um local a tua escolha.
   (ex: C:\Programs\SIC OPTO Downloader\)

2. Abre a pasta extraida e executa o ficheiro:
   $exeName.exe

IMPORTANTE: Nao moves o .exe para fora da pasta.
Todos os ficheiros da pasta sao necessarios para a app funcionar.
"@

# Zipa a partir de dist_win para o ZIP nao incluir o caminho "dist_win" no interior
Push-Location "dist_win"
& $7z a -tzip -mx=5 "..\$zipPath" "$exeName"
$zipExit = $LASTEXITCODE
Pop-Location
if ($zipExit -ne 0) { throw "7-Zip falhou com codigo $zipExit" }
Write-Host "ZIP criado: $zipPath"

# Copia também a pasta descomprimida caso seja útil
$folderDest = "release-dist\$exeName"
if (Test-Path $folderDest) { Remove-Item $folderDest -Recurse -Force }
Copy-Item -Recurse "dist_win\$exeName" $folderDest
Write-Host "Pasta criada: $folderDest"

Write-Host ""
Write-Host "Build concluido."
Write-Host "  EXE:    $folderDest\$exeName.exe"
Write-Host "  ZIP:    $zipPath"