#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
F5_VENV_DIR="${F5_TTS_VENV_DIR:-$BACKEND_DIR/f5_venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -m venv "$F5_VENV_DIR"
"$F5_VENV_DIR/bin/python" -m pip install --upgrade pip
"$F5_VENV_DIR/bin/python" -m pip install -r "$BACKEND_DIR/requirements-f5.txt"

echo "F5-TTS runtime installed at: $F5_VENV_DIR"
echo "Set F5_TTS_PYTHON=$F5_VENV_DIR/bin/python if the app cannot locate it automatically."
