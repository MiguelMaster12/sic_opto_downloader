#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo
echo "=== Opto Downloader - Instalador Linux ==="
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

create_venv() {
  if "$PYTHON_BIN" -m venv .venv; then
    return 0
  fi

  echo
  echo "Falha ao criar .venv. A tentar instalar suporte venv do Python..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3-venv
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm python
  else
    echo "Nao foi possivel instalar venv automaticamente neste Linux." >&2
    echo "Instala o pacote python3-venv e volta a correr ./install_linux.sh" >&2
    exit 1
  fi

  "$PYTHON_BIN" -m venv .venv
}

if [[ ! -d ".venv" ]]; then
  echo "A criar ambiente virtual .venv..."
  create_venv
fi

VENV_PYTHON=".venv/bin/python"

echo "A atualizar pip..."
"$VENV_PYTHON" -m pip install --upgrade pip

echo "A instalar e configurar dependencias..."
"$VENV_PYTHON" instalar_dependencias.py

chmod +x run_linux.sh

echo
echo "[OK] Instalacao concluida."
echo "Para abrir: ./run_linux.sh"
echo

read -r -p "Abrir a ferramenta agora? [s/N] " answer || true
case "${answer:-}" in
  s|S|y|Y) ./run_linux.sh ;;
esac
