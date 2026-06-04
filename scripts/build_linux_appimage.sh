#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -gt 1 ]]; then
  echo "Uso: $0 [versao]" >&2
  exit 1
fi

VERSION="${1:-}"
APP_NAME="sic-opto-downloader"
DISPLAY_NAME="SIC OPTO Downloader"
DIST_DIR="release-dist"
BUILD_DIR="$DIST_DIR/linux-build"
APPDIR="$BUILD_DIR/AppDir"

PACKAGE_NAME="$APP_NAME"
if [[ -n "$VERSION" ]]; then
  PACKAGE_NAME+="-$VERSION"
fi
PACKAGE_NAME+="-linux"

rm -rf "$BUILD_DIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$DIST_DIR"

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller yt-dlp requests pywidevine selenium websocket-client

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "$PACKAGE_NAME" \
  --collect-all pywidevine \
  --collect-all pymp4 \
  --collect-all google \
  v3.py

cp "dist/$PACKAGE_NAME" "$APPDIR/usr/bin/$APP_NAME"
chmod +x "$APPDIR/usr/bin/$APP_NAME"

if [[ -f "assets/app-icon.png" ]]; then
  cp "assets/app-icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
fi

cat > "$APPDIR/usr/share/applications/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$DISPLAY_NAME
Exec=$APP_NAME
Icon=$APP_NAME
Categories=AudioVideo;Network;
Terminal=false
EOF

cp "$APPDIR/usr/share/applications/$APP_NAME.desktop" "$APPDIR/$APP_NAME.desktop"
if [[ -f "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png" ]]; then
  cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png" "$APPDIR/$APP_NAME.png"
fi

LINUXDEPLOY="$BUILD_DIR/linuxdeploy-x86_64.AppImage"
curl -L \
  "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage" \
  -o "$LINUXDEPLOY"
chmod +x "$LINUXDEPLOY"

ARCH=x86_64 "$LINUXDEPLOY" --appdir "$APPDIR" --output appimage

mv ./*.AppImage "$DIST_DIR/$PACKAGE_NAME.AppImage"
rm -rf "$BUILD_DIR"

echo "AppImage criada: $DIST_DIR/$PACKAGE_NAME.AppImage"
