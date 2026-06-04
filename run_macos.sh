#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Ambiente .venv nao encontrado. Corre primeiro: ./install_macos.sh" >&2
  exit 1
fi

".venv/bin/python" v3.py
