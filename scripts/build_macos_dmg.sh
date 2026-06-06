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
APP_NAME="opto-downloader"
DISPLAY_NAME="Opto Downloader"
DIST_DIR="release-dist"
STAGING_DIR="$DIST_DIR/dmg-staging"
ICON_SOURCE="assets/app-icon.png"

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
cp opto_app.py "$RESOURCES_DIR/"
cp opto_api_scraper.py "$RESOURCES_DIR/"
cp opto_api_media_resolver.py "$RESOURCES_DIR/"
cp instalar_dependencias.py "$RESOURCES_DIR/"
cp platform/macos/install_macos.sh "$RESOURCES_DIR/"
cp platform/macos/run_macos.sh "$RESOURCES_DIR/"
cp config/sic_opto_config.example.json "$RESOURCES_DIR/config/"
if [[ -d "assets" ]]; then
  cp -r assets "$RESOURCES_DIR/assets"
  find "$RESOURCES_DIR/assets" -name ".DS_Store" -delete
fi

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
SUPPORT_DIR="$HOME/Library/Application Support/Opto Downloader"
LOG_DIR="$HOME/Library/Logs/Opto Downloader"
LOG_FILE="$LOG_DIR/app.log"

export PATH="/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:/opt/homebrew/bin:$SUPPORT_DIR/vendor/bin:$PATH"

mkdir -p "$SUPPORT_DIR/config" "$LOG_DIR"

{
  echo
  echo "=== Opto Downloader - $(date) ==="
} >> "$LOG_FILE"

copy_runtime_files() {
  cp "$APP_RESOURCES/README.md" "$SUPPORT_DIR/README.md"
  cp "$APP_RESOURCES/opto_app.py" "$SUPPORT_DIR/opto_app.py"
  cp "$APP_RESOURCES/opto_api_scraper.py" "$SUPPORT_DIR/opto_api_scraper.py"
  cp "$APP_RESOURCES/opto_api_media_resolver.py" "$SUPPORT_DIR/opto_api_media_resolver.py"
  cp "$APP_RESOURCES/instalar_dependencias.py" "$SUPPORT_DIR/instalar_dependencias.py"
  cp "$APP_RESOURCES/install_macos.sh" "$SUPPORT_DIR/install_macos.sh"
  cp "$APP_RESOURCES/run_macos.sh" "$SUPPORT_DIR/run_macos.sh"
  if [[ -d "$APP_RESOURCES/assets" ]]; then
    rm -rf "$SUPPORT_DIR/assets"
    cp -r "$APP_RESOURCES/assets" "$SUPPORT_DIR/assets"
    find "$SUPPORT_DIR/assets" -name ".DS_Store" -delete
  fi
  if [[ ! -f "$SUPPORT_DIR/config/sic_opto_config.example.json" ]]; then
    cp "$APP_RESOURCES/config/sic_opto_config.example.json" "$SUPPORT_DIR/config/"
  fi
  chmod +x "$SUPPORT_DIR/install_macos.sh" "$SUPPORT_DIR/run_macos.sh"
}

show_dialog() {
  /usr/bin/osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with title \"Opto Downloader\"" >/dev/null 2>&1 || true
}

copy_runtime_files >> "$LOG_FILE" 2>&1
cd "$SUPPORT_DIR"

run_install_with_window() {
  "$PYTHON_FOR_INSTALL" - <<'PY'
import queue
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QLabel, QProgressBar,
    QTextEdit, QVBoxLayout, QWidget,
)

root_dir = Path.cwd()
log_file = Path.home() / "Library" / "Logs" / "Opto Downloader" / "app.log"
q = queue.Queue()

app = QApplication(sys.argv)
app.setApplicationName("Opto Downloader")

win = QWidget()
win.setWindowTitle("Opto Downloader — Instalação")
win.resize(820, 520)
win.setStyleSheet("""
    QWidget  { background: #F6F4EF; color: #1F1D1A;
               font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 13px; }
    QTextEdit { background: #FFFFFF; border: 1px solid #DDD7CC;
                border-radius: 10px; padding: 10px;
                font-family: Menlo, Consolas, monospace; font-size: 12px; }
    QProgressBar { background: #F0EDE7; border: 1px solid #DDD7CC;
                   border-radius: 6px; height: 8px; }
    QProgressBar::chunk { background: #181613; border-radius: 5px; }
""")

layout = QVBoxLayout(win)
layout.setContentsMargins(24, 20, 24, 20)
layout.setSpacing(10)

header = QLabel("A preparar o Opto Downloader")
header.setFont(QFont("", 15, QFont.Weight.Bold))
layout.addWidget(header)

details = QLabel(
    "A primeira abertura instala dependências locais e ferramentas necessárias.\n"
    "A app abre automaticamente quando terminar.\n"
    f"Pasta da aplicação: {root_dir}"
)
details.setWordWrap(True)
details.setStyleSheet("color: #756E66;")
layout.addWidget(details)

status_lbl = QLabel("A iniciar preparação...")
status_lbl.setStyleSheet("font-weight: 600;")
layout.addWidget(status_lbl)

progress = QProgressBar()
progress.setRange(0, 0)   # indeterminate
layout.addWidget(progress)

log_box = QTextEdit()
log_box.setReadOnly(True)
layout.addWidget(log_box, 1)

win.show()

def append(text):
    log_box.append(text.rstrip())
    sb = log_box.verticalScrollBar()
    sb.setValue(sb.maximum())

def poll():
    try:
        while True:
            kind, value = q.get_nowait()
            if kind == "line":
                append(value)
                lower = value.lower()
                if "a instalar" in lower or "[ok]" in lower:
                    status_lbl.setText(value.strip())
            elif kind == "done":
                progress.setRange(0, 1)
                progress.setValue(1)
                if value == 0:
                    status_lbl.setText("Instalação concluída. A abrir aplicação...")
                    QTimer.singleShot(900, app.quit)
                else:
                    status_lbl.setText(f"Instalação falhou (código {value}).")
                    append(f"\nInstalação falhou (código {value}).\n")
            elif kind == "error":
                progress.setRange(0, 1)
                progress.setValue(0)
                status_lbl.setText("Instalação falhou.")
                append(f"\nErro: {value}\n")
    except queue.Empty:
        pass

timer = QTimer()
timer.timeout.connect(poll)
timer.start(100)

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
        q.put(("done", proc.wait()))
    except Exception as exc:
        q.put(("error", str(exc)))

threading.Thread(target=worker, daemon=True).start()
sys.exit(app.exec())
PY
}

needs_install=0
if [[ ! -x ".venv/bin/python" ]]; then
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
from PySide6.QtWidgets import QApplication
PY
    then
      PYTHON_FOR_INSTALL="$candidate"
      break
    fi
  done

  if [[ -n "$PYTHON_FOR_INSTALL" ]]; then
    if ! run_install_with_window >> "$LOG_FILE" 2>&1; then
      show_dialog "A instalacao falhou. Ve o log em ~/Library/Logs/Opto Downloader/app.log"
      exit 1
    fi
  elif ! printf 'n\n' | ./install_macos.sh >> "$LOG_FILE" 2>&1; then
    show_dialog "A instalacao falhou. Ve o log em ~/Library/Logs/Opto Downloader/app.log"
    exit 1
  fi
fi

if ! ".venv/bin/python" opto_app.py >> "$LOG_FILE" 2>&1; then
  show_dialog "A aplicacao fechou com erro. Ve o log em ~/Library/Logs/Opto Downloader/app.log"
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
  <string>pt.optodownloader.app</string>
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
  -volname "Opto Downloader" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH" >/dev/null

rm -rf "$STAGING_DIR"

echo "DMG criado: $DMG_PATH"
