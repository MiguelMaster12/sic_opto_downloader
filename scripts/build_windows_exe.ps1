param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Join-Path $PSScriptRoot "..")

$appName = "opto-downloader"
$displayName = "Opto Downloader"
$publisher = "Opto Downloader"
$name = $appName
if ($Version) {
    $name = "$name-$Version"
}
$distName = "$name-windows"
$setupName = "$name-windows-setup"
$appExeName = "$distName.exe"
$buildDir = Join-Path "dist" $distName
$issPath = Join-Path "build" "$setupName.iss"

$isccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$isccPath = if ($isccCommand) { $isccCommand.Source } else { $null }
if (-not $isccPath) {
    $innoPaths = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )

    foreach ($candidate in $innoPaths) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            $isccPath = $candidate
            break
        }
    }
}

if (-not $isccPath) {
    throw "Inno Setup 6 nao encontrado. Instala-o e volta a correr este script: winget install JRSoftware.InnoSetup"
}

python -m pip install --upgrade pip
python -m pip install pyinstaller PySide6 yt-dlp requests pywidevine
$env:OPTO_FORCE_VENDOR_TOOLS = "1"
python instalar_dependencias.py
Remove-Item Env:\OPTO_FORCE_VENDOR_TOOLS -ErrorAction SilentlyContinue

$dataSep = ";"
$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", $distName,
    "--add-data", "assets${dataSep}assets",
    "--add-data", "vendor${dataSep}vendor",
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
New-Item -ItemType Directory -Force -Path "build" | Out-Null
$sourceDir = (Resolve-Path -LiteralPath $buildDir).Path
$outputDir = (Resolve-Path -LiteralPath "release-dist").Path

$iconLine = ""
if (Test-Path -LiteralPath "assets\app-icon.ico") {
    $iconPath = (Resolve-Path -LiteralPath "assets\app-icon.ico").Path
    $iconLine = "SetupIconFile=$iconPath"
}

$appVersion = if ($Version) { $Version.TrimStart("v") } else { "1.0.0" }
$issContent = @"
#define AppName "$displayName"
#define AppPublisher "$publisher"
#define AppVersion "$appVersion"
#define AppExeName "$appExeName"
#define SourceDir "$sourceDir"
#define OutputDir "$outputDir"
#define OutputBaseFilename "$setupName"

[Setup]
AppId={{9B4D7A93-98EC-4C2E-9B31-36B0A52E7442}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=no
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#AppExeName}
$iconLine

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
"@

Set-Content -LiteralPath $issPath -Value $issContent -Encoding UTF8

& $isccPath $issPath
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao criar instalador com Inno Setup (codigo $LASTEXITCODE)."
}

$setupPath = Join-Path "release-dist" "$setupName.exe"
if (-not (Test-Path -LiteralPath $setupPath)) {
    throw "Instalador nao encontrado depois do build: $setupPath"
}

Write-Host "Instalador criado: $setupPath"
Get-ChildItem -LiteralPath "release-dist" | Format-Table Name, Length
