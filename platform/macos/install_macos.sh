#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo
echo "=== SIC OPTO Downloader - Instalador macOS ==="
echo

find_python() {
  for py in python3 python; do
    if command -v "$py" >/dev/null 2>&1; then
      if "$py" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
      then
        echo "$py"
        return 0
      fi
    fi
  done
  echo "Python 3.9+ nao encontrado. Instala Python 3 e volta a correr este script." >&2
  exit 1
}

PYTHON_BIN="$(find_python)"

if [[ ! -d ".venv" ]]; then
  echo "A criar ambiente virtual .venv..."
  "$PYTHON_BIN" -m venv .venv
fi

VENV_PYTHON=".venv/bin/python"

echo "A atualizar pip..."
"$VENV_PYTHON" -m pip install --upgrade pip

echo "A instalar e configurar dependencias..."
"$VENV_PYTHON" instalar_dependencias.py

chmod +x run_macos.sh

echo
echo "[OK] Instalacao concluida."
echo "Para abrir: ./run_macos.sh"
echo

read -r -p "Abrir a ferramenta agora? [s/N] " answer || true
case "${answer:-}" in
  s|S|y|Y) ./run_macos.sh ;;
esac
