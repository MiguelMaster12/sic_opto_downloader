#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "hdiutil nao encontrado. Este script tem de correr em macOS." >&2
  exit 1
fi

if ! command -v sips >/dev/null 2>&1 || ! command -v iconutil >/dev/null 2>&1; then
  echo "sips/iconutil nao encontrados. Este script tem de correr em macOS." >&2
  exit 1
fi

if [[ $# -gt 1 ]]; then
  echo "Uso: $0 [versao]" >&2
  exit 1
fi

VERSION="${1:-}"
APP_NAME="sic-opto-downloader"
DISPLAY_NAME="SIC OPTO Downloader"
DIST_DIR="release-dist"
STAGING_DIR="$DIST_DIR/dmg-staging"
ICON_SOURCE="assets/app-icon.png"
if [[ ! -f "$ICON_SOURCE" && -f "ChatGPT Image 4_06_2026, 15_43_40.png" ]]; then
  ICON_SOURCE="ChatGPT Image 4_06_2026, 15_43_40.png"
fi

DMG_NAME="$APP_NAME"
if [[ -n "$VERSION" ]]; then
  DMG_NAME+="-$VERSION"
fi
DMG_NAME+="-macos.dmg"

APP_BUNDLE="$STAGING_DIR/$DISPLAY_NAME.app"
CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
DMG_PATH="$DIST_DIR/$DMG_NAME"

rm -rf "$STAGING_DIR" "$DMG_PATH"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR/config"

cp README.md "$RESOURCES_DIR/"
cp v3.py "$RESOURCES_DIR/"
cp instalar_dependencias.py "$RESOURCES_DIR/"
cp platform/macos/install_macos.sh "$RESOURCES_DIR/"
cp platform/macos/run_macos.sh "$RESOURCES_DIR/"
cp config/sic_opto_config.example.json "$RESOURCES_DIR/config/"

if [[ -f "$ICON_SOURCE" ]]; then
  ICONSET_DIR="$STAGING_DIR/app-icon.iconset"
  mkdir -p "$ICONSET_DIR"

  sips -z 16 16     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null

  iconutil -c icns "$ICONSET_DIR" -o "$RESOURCES_DIR/app-icon.icns"
  rm -rf "$ICONSET_DIR"
else
  echo "Aviso: icone nao encontrado em '$ICON_SOURCE'. A app sera criada sem icone customizado." >&2
fi

cat > "$MACOS_DIR/$DISPLAY_NAME" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_RESOURCES="$(cd "$(dirname "$0")/../Resources" && pwd)"
SUPPORT_DIR="$HOME/Library/Application Support/SIC OPTO Downloader"
LOG_DIR="$HOME/Library/Logs/SIC OPTO Downloader"
LOG_FILE="$LOG_DIR/app.log"

export PATH="/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:/opt/homebrew/bin:$SUPPORT_DIR/vendor/bin:$PATH"

mkdir -p "$SUPPORT_DIR/config" "$LOG_DIR"

{
  echo
  echo "=== SIC OPTO Downloader - $(date) ==="
} >> "$LOG_FILE"

copy_runtime_files() {
  cp "$APP_RESOURCES/README.md" "$SUPPORT_DIR/README.md"
  cp "$APP_RESOURCES/v3.py" "$SUPPORT_DIR/v3.py"
  cp "$APP_RESOURCES/instalar_dependencias.py" "$SUPPORT_DIR/instalar_dependencias.py"
  cp "$APP_RESOURCES/install_macos.sh" "$SUPPORT_DIR/install_macos.sh"
  cp "$APP_RESOURCES/run_macos.sh" "$SUPPORT_DIR/run_macos.sh"
  if [[ ! -f "$SUPPORT_DIR/config/sic_opto_config.example.json" ]]; then
    cp "$APP_RESOURCES/config/sic_opto_config.example.json" "$SUPPORT_DIR/config/"
  fi
  chmod +x "$SUPPORT_DIR/install_macos.sh" "$SUPPORT_DIR/run_macos.sh"
}

show_dialog() {
  /usr/bin/osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with title \"SIC OPTO Downloader\"" >/dev/null 2>&1 || true
}

copy_runtime_files >> "$LOG_FILE" 2>&1
cd "$SUPPORT_DIR"

run_install_with_window() {
  "$PYTHON_FOR_INSTALL" - <<'PY'
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

root_dir = Path.cwd()
log_file = Path.home() / "Library" / "Logs" / "SIC OPTO Downloader" / "app.log"
q = queue.Queue()

root = tk.Tk()
root.title("SIC OPTO Downloader - Instalação")
root.geometry("760x460")
root.resizable(True, True)

header = tk.Label(
    root,
    text="A preparar a aplicação. Isto pode demorar alguns minutos.",
    font=("Helvetica", 13, "bold"),
    anchor="w",
    padx=14,
    pady=10,
)
header.pack(fill="x")

status = tk.StringVar(value="A iniciar instalação...")
tk.Label(root, textvariable=status, anchor="w", padx=14).pack(fill="x")

log = scrolledtext.ScrolledText(root, height=18, wrap="word")
log.pack(fill="both", expand=True, padx=14, pady=(8, 12))
log.configure(state="disabled")

def append(text):
    log.configure(state="normal")
    log.insert("end", text)
    log.see("end")
    log.configure(state="disabled")

def worker():
    try:
        proc = subprocess.Popen(
            ["./install_macos.sh"],
            cwd=root_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if proc.stdin:
            proc.stdin.write("n\n")
            proc.stdin.flush()
            proc.stdin.close()
        with log_file.open("a", encoding="utf-8", errors="replace") as fh:
            for line in proc.stdout or []:
                fh.write(line)
                fh.flush()
                q.put(("line", line))
        code = proc.wait()
        q.put(("done", code))
    except Exception as exc:
        q.put(("error", str(exc)))

def poll():
    try:
        while True:
            kind, value = q.get_nowait()
            if kind == "line":
                append(value)
                lower = value.lower()
                if "a instalar" in lower:
                    status.set(value.strip())
                elif "[ok]" in lower:
                    status.set(value.strip())
            elif kind == "done":
                if value == 0:
                    status.set("Instalação concluída. A abrir aplicação...")
                    root.after(900, root.destroy)
                else:
                    status.set(f"Instalação falhou (código {value}).")
                    append(f"\nInstalação falhou (código {value}).\n")
            elif kind == "error":
                status.set("Instalação falhou.")
                append(f"\nErro: {value}\n")
    except queue.Empty:
        pass
    if root.winfo_exists():
        root.after(100, poll)

threading.Thread(target=worker, daemon=True).start()
root.after(100, poll)
root.mainloop()
PY
}

needs_install=0
if [[ ! -x ".venv/bin/python" ]]; then
  needs_install=1
elif ! ".venv/bin/python" - <<'PY' >> "$LOG_FILE" 2>&1
import tkinter
PY
then
  echo "A recriar .venv: Python sem Tkinter funcional detectado." >> "$LOG_FILE"
  rm -rf ".venv"
  needs_install=1
fi

if [[ "$needs_install" -eq 1 ]]; then
  PYTHON_FOR_INSTALL=""
  for candidate in \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/bin/python3 \
    python3 \
    python
  do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" - <<'PY' >/dev/null 2>&1
import tkinter
PY
    then
      PYTHON_FOR_INSTALL="$candidate"
      break
    fi
  done

  if [[ -n "$PYTHON_FOR_INSTALL" ]]; then
    if ! run_install_with_window >> "$LOG_FILE" 2>&1; then
      show_dialog "A instalacao falhou. Ve o log em ~/Library/Logs/SIC OPTO Downloader/app.log"
      exit 1
    fi
  elif ! printf 'n\n' | ./install_macos.sh >> "$LOG_FILE" 2>&1; then
    show_dialog "A instalacao falhou. Ve o log em ~/Library/Logs/SIC OPTO Downloader/app.log"
    exit 1
  fi
fi

if ! ".venv/bin/python" v3.py >> "$LOG_FILE" 2>&1; then
  show_dialog "A aplicacao fechou com erro. Ve o log em ~/Library/Logs/SIC OPTO Downloader/app.log"
  exit 1
fi
EOF

chmod +x "$MACOS_DIR/$DISPLAY_NAME"

cat > "$CONTENTS_DIR/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>pt</string>
  <key>CFBundleDisplayName</key>
  <string>$DISPLAY_NAME</string>
  <key>CFBundleExecutable</key>
  <string>$DISPLAY_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>pt.sicopto.downloader</string>
  <key>CFBundleIconFile</key>
  <string>app-icon.icns</string>
  <key>CFBundleName</key>
  <string>$DISPLAY_NAME</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>${VERSION:-1.0.0}</string>
  <key>CFBundleVersion</key>
  <string>${VERSION:-1.0.0}</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.15</string>
  <key>LSUIElement</key>
  <false/>
</dict>
</plist>
EOF

ln -s /Applications "$STAGING_DIR/Applications"

hdiutil create \
  -volname "SIC OPTO Downloader" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH" >/dev/null

rm -rf "$STAGING_DIR"

echo "DMG criado: $DMG_PATH"
