#!/usr/bin/env python3
"""
Instalador de Dependências — Opto Downloader
=================================================
Corre este script UMA VEZ antes de usar o opto_app.py
"""

import sys
import os
import subprocess
import platform
import shutil
import json
import urllib.request
import zipfile
import tarfile
import tempfile
from pathlib import Path

PLATFORM = platform.system()  # Windows / Linux / Darwin
PROJECT_DIR = Path(__file__).resolve().parent
VENDOR_DIR = PROJECT_DIR / "vendor"
BIN_DIR = VENDOR_DIR / "bin"
TOOLS_DIR = VENDOR_DIR / "tools"
SECRETS_DIR = PROJECT_DIR / "secrets"
CONFIG_DIR = PROJECT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "sic_opto_config.json"

# ── Saída/cores no terminal ──────────────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def c(code, text): return f"\033[{code}m{text}\033[0m" if sys.platform != "win32" or os.environ.get("WT_SESSION") else text
RED    = lambda t: c("91", t)
GREEN  = lambda t: c("92", t)
YELLOW = lambda t: c("93", t)
CYAN   = lambda t: c("96", t)
BOLD   = lambda t: c("1",  t)

def ok(msg):   print(f"  {GREEN('[OK]')} {msg}")
def warn(msg): print(f"  {YELLOW('[!]')} {msg}")
def err(msg):  print(f"  {RED('[X]')} {msg}")
def info(msg): print(f"  {CYAN('->')} {msg}")
def sep():     print(f"\n{'─'*54}")

DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "application/zip,application/octet-stream,*/*",
    "Referer": "https://www.bento4.com/downloads/",
}

def download_file(url, dest_path):
    req = urllib.request.Request(url, headers=DOWNLOAD_HEADERS)
    with urllib.request.urlopen(req, timeout=120) as response:
        with open(dest_path, "wb") as out:
            shutil.copyfileobj(response, out)

def fetch_json(url):
    headers = dict(DOWNLOAD_HEADERS)
    headers["Accept"] = "application/vnd.github+json,application/json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))

# ── Pip install helper ────────────────────────────────────────────────────────
def pip_install(package, import_name=None, extra_args=None):
    import_name = import_name or package.split("[")[0].replace("-", "_")
    try:
        __import__(import_name)
        ok(f"{package} já instalado")
        return True
    except ImportError:
        pass

    info(f"A instalar {package}...")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package]
    if extra_args:
        cmd += extra_args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"{package} instalado com sucesso")
        return True
    else:
        err(f"Falha ao instalar {package}")
        print(f"    {result.stderr[-400:]}")
        return False


# ── Verificar ferramenta externa ──────────────────────────────────────────────
def resolve_tool(name):
    """Procura no PATH e nas pastas locais usadas pelo opto_app.py."""
    if not name:
        return None

    candidates = [name]
    if PLATFORM == "Windows" and not name.lower().endswith(".exe"):
        candidates.append(f"{name}.exe")

    for candidate in candidates:
        candidate_path = Path(candidate)
        if candidate_path.is_file():
            return str(candidate_path)
        path = shutil.which(candidate)
        if path:
            return path

    for folder in (
        BIN_DIR,
        TOOLS_DIR,
        PROJECT_DIR / "bin",
        PROJECT_DIR / "tools",
        PROJECT_DIR,
    ):
        if not folder.exists():
            continue
        for candidate in candidates:
            if Path(candidate).parent != Path("."):
                continue
            direct = folder / candidate
            if direct.is_file():
                return str(direct)
            hits = list(folder.rglob(candidate))
            if hits:
                return str(hits[0])

    return None


def check_tool(name):
    path = resolve_tool(name)
    if path:
        ok(f"{name} encontrado: {path}")
        return True
    else:
        warn(f"{name} não encontrado no PATH")
        return False


# ── Instalar ffmpeg ───────────────────────────────────────────────────────────
def install_ffmpeg():
    if check_tool("ffmpeg"):
        return True

    print()
    info("A tentar instalar ffmpeg automaticamente...")

    if PLATFORM == "Darwin":
        # Homebrew
        if shutil.which("brew"):
            r = subprocess.run(["brew", "install", "ffmpeg"], capture_output=True, text=True)
            if r.returncode == 0:
                ok("ffmpeg instalado via Homebrew")
                return True
        warn("Homebrew não encontrado. Instala manualmente:")
        print("    https://ffmpeg.org/download.html")
        return False

    elif PLATFORM == "Linux":
        for mgr, cmd in [
            ("apt-get", ["sudo", "apt-get", "install", "-y", "ffmpeg"]),
            ("dnf",     ["sudo", "dnf", "install", "-y", "ffmpeg"]),
            ("pacman",  ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"]),
        ]:
            if shutil.which(mgr):
                info(f"A usar {mgr}...")
                r = subprocess.run(cmd)
                if r.returncode == 0:
                    ok("ffmpeg instalado")
                    return True
        warn("Não foi possível instalar automaticamente. Instala manualmente:")
        print("    sudo apt install ffmpeg")
        return False

    elif PLATFORM == "Windows":
        # Descarregar binário ffmpeg para vendor/tools.
        info("A descarregar ffmpeg para Windows...")
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        dest_dir = TOOLS_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            zip_path = dest_dir / "ffmpeg.zip"
            info("A descarregar (pode demorar)...")
            download_file(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(dest_dir)
            zip_path.unlink()
            # Encontrar ffmpeg.exe
            exes = list(dest_dir.rglob("ffmpeg.exe"))
            if exes:
                ffmpeg_path = exes[0].parent
                # Adicionar ao PATH da sessão atual
                os.environ["PATH"] = str(ffmpeg_path) + os.pathsep + os.environ["PATH"]
                ok(f"ffmpeg descarregado: {ffmpeg_path}")
                warn("Adiciona esta pasta ao PATH do Windows para uso futuro:")
                print(f"    {ffmpeg_path}")
                return True
        except Exception as e:
            err(f"Erro ao descarregar ffmpeg: {e}")
        warn("Instala manualmente: https://ffmpeg.org/download.html")
        return False

    return False


# ── Instalar mp4decrypt (Bento4) ──────────────────────────────────────────────
def install_mp4decrypt():
    if check_tool("mp4decrypt"):
        return True

    print()
    info("A tentar instalar mp4decrypt (Bento4)...")

    if PLATFORM == "Linux":
        for mgr, cmd in [
            ("apt-get", ["sudo", "apt-get", "install", "-y", "bento4"]),
            ("dnf",     ["sudo", "dnf", "install", "-y", "bento4"]),
        ]:
            if shutil.which(mgr):
                r = subprocess.run(cmd)
                if r.returncode == 0 and shutil.which("mp4decrypt"):
                    ok("mp4decrypt instalado")
                    return True
        # pip install bento4 (wrapper)
        r = subprocess.run([sys.executable, "-m", "pip", "install", "bento4"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            ok("bento4 instalado via pip")
            return True

    dest_dir = TOOLS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    urls = {
        "Windows": [
            "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-microsoft-win32.zip",
        ],
        "Darwin": [
            "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.universal-apple-macosx.zip",
        ],
        "Linux": [
            "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip",
        ],
    }
    platform_urls = urls.get(PLATFORM)
    if not platform_urls:
        warn("Plataforma não suportada para download automático.")
        return False

    try:
        zip_path = dest_dir / "bento4.zip"
        last_error = None
        for url in platform_urls:
            try:
                info(f"A descarregar Bento4: {url}")
                download_file(url, zip_path)
                last_error = None
                break
            except Exception as e:
                last_error = e
                warn(f"Falhou este link: {e}")
        if last_error:
            raise last_error

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(dest_dir)
        zip_path.unlink()

        # Encontrar mp4decrypt
        exe_name = "mp4decrypt.exe" if PLATFORM == "Windows" else "mp4decrypt"
        exes = list(dest_dir.rglob(exe_name))
        if exes:
            mp4d = exes[0]
            if PLATFORM != "Windows":
                mp4d.chmod(0o755)
            # Copiar para vendor/bin para coincidir com o opto_app.py
            final_dir = BIN_DIR
            final_dir.mkdir(parents=True, exist_ok=True)
            final = final_dir / exe_name
            shutil.copy2(mp4d, final)
            if PLATFORM != "Windows":
                final.chmod(0o755)
            # Adicionar ao PATH desta sessão
            os.environ["PATH"] = str(final.parent) + os.pathsep + os.environ["PATH"]
            ok(f"mp4decrypt instalado: {final}")
            warn("Adiciona esta pasta ao PATH do sistema para uso futuro:")
            print(f"    {final.parent}")
            return True
    except Exception as e:
        err(f"Erro ao descarregar Bento4: {e}")

    warn("Instala manualmente: https://www.bento4.com/downloads/")
    return False


# ── Verificar .wvd ────────────────────────────────────────────────────────────
def check_wvd():
    wvd_files = list(SECRETS_DIR.glob("*.wvd")) + \
                list(PROJECT_DIR.glob("*.wvd")) + \
                list(Path.home().glob("*.wvd")) + \
                list(Path.home().glob(".wvd/*.wvd"))

    if wvd_files:
        ok(f"device.wvd encontrado: {wvd_files[0]}")
        return True
    else:
        warn("Nenhum ficheiro .wvd encontrado")
        print(f"""
    {YELLOW('O ficheiro .wvd é o teu CDM Widevine pessoal.')}
    É necessário para desencriptar sem depender de sites externos.

    Como obter:
      1. Tens de o extrair de um dispositivo Android (telemóvel/tablet)
         com a tua conta SIC OPTO ativa.
      2. Ferramentas comuns: dumper WVD para Android.
      3. Coloca o ficheiro 'device.wvd' nesta pasta:
         {SECRETS_DIR}

    {YELLOW('Sem o .wvd podes inserir as keys manualmente na aba Avançado.')}
""")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    print()
    print(BOLD("╔══════════════════════════════════════════════╗"))
    print(BOLD("║   Opto Downloader — Dependências             ║"))
    print(BOLD("╚══════════════════════════════════════════════╝"))
    print(f"  Python {sys.version.split()[0]} | {PLATFORM}")

    results = {}

    # ── 1. Pacotes Python
    sep()
    print(BOLD("  1. Pacotes Python (pip)"))
    print()

    pkgs = [
        ("PySide6",          "PySide6",    None),
        ("yt-dlp",           "yt_dlp",     None),
        ("requests",         "requests",   None),
        ("pywidevine",       "pywidevine", None),
    ]
    for pkg, imp, extra in pkgs:
        results[pkg] = pip_install(pkg, imp, extra)

    # ── 2. ffmpeg
    sep()
    print(BOLD("  2. ffmpeg"))
    print()
    results["ffmpeg"] = install_ffmpeg()

    # ── 3. mp4decrypt
    sep()
    print(BOLD("  3. mp4decrypt (Bento4)"))
    print()
    results["mp4decrypt"] = install_mp4decrypt()

    # ── 4. .wvd
    sep()
    print(BOLD("  4. Ficheiro CDM Widevine (.wvd)"))
    print()
    results["wvd"] = check_wvd()

    # ── Sumário
    sep()
    print(BOLD("  SUMÁRIO"))
    print()
    all_ok = True
    for name, status in results.items():
        if status:
            ok(f"{name}")
        else:
            warn(f"{name} — requer atenção manual")
            if name != "wvd":
                all_ok = False

    print()
    if all_ok:
        print(GREEN(BOLD("  [OK] Tudo instalado! Podes correr: python opto_app.py")))
    else:
        print(YELLOW(BOLD("  ⚠ Algumas dependências precisam de instalação manual.")))
        print(YELLOW("    Consulta as instruções acima e o ficheiro README.md"))
    print()


if __name__ == "__main__":
    main()
