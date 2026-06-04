#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v zip >/dev/null 2>&1; then
  echo "zip nao encontrado." >&2
  exit 1
fi

if [[ $# -gt 1 ]]; then
  echo "Uso: $0 [versao]" >&2
  exit 1
fi

VERSION="${1:-}"
APP_NAME="sic-opto-downloader"
DIST_DIR="release-dist"
STAGING_DIR="$DIST_DIR/zip-staging"

COMMON_FILES=(
  "README.md"
  "v3.py"
  "instalar_dependencias.py"
  "config/sic_opto_config.example.json"
)

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

copy_common_files() {
  local target_dir="$1"
  mkdir -p "$target_dir/config"
  for file in "${COMMON_FILES[@]}"; do
    cp "$file" "$target_dir/$file"
  done
}

package_platform() {
  local platform="$1"
  shift

  local package_name="$APP_NAME"
  if [[ -n "$VERSION" ]]; then
    package_name+="-$VERSION"
  fi
  package_name+="-$platform"

  local package_dir="$STAGING_DIR/$package_name"
  local zip_file="$DIST_DIR/$package_name.zip"

  rm -f "$zip_file"
  mkdir -p "$package_dir"
  copy_common_files "$package_dir"

  for file in "$@"; do
    cp "$file" "$package_dir/$(basename "$file")"
  done

  case "$platform" in
    linux)
      chmod +x "$package_dir/install_linux.sh" "$package_dir/run_linux.sh"
      ;;
    macos)
      chmod +x "$package_dir/install_macos.sh" "$package_dir/run_macos.sh"
      ;;
  esac

  (
    cd "$STAGING_DIR"
    zip -qr "../$(basename "$zip_file")" "$package_name"
  )

  echo "ZIP criado: $zip_file"
}

mkdir -p "$DIST_DIR"

package_platform "windows" \
  "platform/windows/install_windows.bat" \
  "platform/windows/install_windows.ps1" \
  "platform/windows/run_windows.bat" \
  "platform/windows/run_windows.ps1"

package_platform "macos" \
  "platform/macos/install_macos.sh" \
  "platform/macos/run_macos.sh"

package_platform "linux" \
  "platform/linux/install_linux.sh" \
  "platform/linux/run_linux.sh"

rm -rf "$STAGING_DIR"
